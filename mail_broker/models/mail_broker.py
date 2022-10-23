# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools


class MailBroker(models.Model):
    _name = "mail.broker"
    _inherit = ["collection.base"]
    _description = "Mail Broker"

    name = fields.Char(required=True)
    token = fields.Char(required=True)
    broker_type = fields.Selection([], required=True)
    show_on_app = fields.Boolean(default=True)
    webhook_key = fields.Char()
    webhook_secret = fields.Char()
    integrated_webhook_state = fields.Selection(
        [("pending", "Pending"), ("integrated", "Integrated")], readonly=True
    )
    can_set_webhook = fields.Boolean(compute="_compute_webhook_checks")
    webhook_url = fields.Char(compute="_compute_webhook_url")
    has_new_channel_security = fields.Boolean(
        help="When checked, channels are not created automatically"
    )
    webhook_user_id = fields.Many2one(
        "res.users", default=lambda self: self.env.user.id
    )

    _sql_constraints = [
        ("mail_broker_token", "unique(token)", "Token must be unique"),
        (
            "mail_broker_webhook_key",
            "unique(webhook_key)",
            "Webhook Key must be unique",
        ),
    ]

    @api.depends("webhook_key")
    def _compute_webhook_url(self):
        for record in self:
            record.webhook_url = record._get_webhook_url()

    def _get_channel_id(self, chat_token):
        return (
            self.env["mail.broker.channel"]
            .search(
                [("token", "=", str(chat_token)), ("broker_id", "=", self.id)], limit=1,
            )
            .id
        )

    def _get_webhook_url(self):
        return "%s/broker/%s/%s/update" % (
            self.webhook_url
            or self.env["ir.config_parameter"].get_param("web.base.url"),
            self.broker_type,
            self.webhook_key,
        )

    def _can_set_webhook(self):
        return self.webhook_key and self.webhook_user_id

    @api.depends("broker_type")
    def _compute_webhook_checks(self):
        for record in self:
            record.can_set_webhook = record._can_set_webhook()

    def set_webhook(self):
        self.ensure_one()
        if self.can_set_webhook:
            with self.work_on(self._name) as work:
                work.component(usage=self.broker_type)._set_webhook()

    def remove_webhook(self):
        self.ensure_one()
        with self.work_on(self._name) as work:
            work.component(usage=self.broker_type)._remove_webhook()

    def update_webhook(self):
        self.ensure_one()
        self.remove_webhook()
        self.set_webhook()

    @api.model
    def broker_fetch_slot(self):
        result = []
        for record in self.search([("show_on_app", "=", True)]):

            result.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "channel_name": "broker_%s" % record.id,
                    "threads": [
                        thread._get_thread_data()
                        for thread in self.env["mail.broker.channel"].search(
                            [("show_on_app", "=", True), ("broker_id", "=", record.id)]
                        )
                    ],
                }
            )
        return result

    def channel_search(self, name):
        self.ensure_one()
        domain = [("broker_id", "=", self.id)]
        if name:
            domain += [("name", "ilike", "%" + name + "%")]
        return self.env["mail.broker.channel"].search(domain).read(["name"])

    def write(self, vals):
        res = super(MailBroker, self).write(vals)
        if (
            "webhook_key" in vals
            or "integrated_webhook_state" in vals
            or "webhook_secret" in vals
            or "webhook_user_id" in vals
        ):
            self.clear_caches()
        return res

    @api.model_create_single
    def create(self, vals):
        res = super(MailBroker, self).create(vals)
        if (
            "webhook_key" in vals
            or "integrated_webhook_state" in vals
            or "webhook_secret" in vals
            or "webhook_user_id" in vals
        ):
            self.clear_caches()
        return res

    @api.model
    @tools.ormcache()
    def _get_broker_map(self, state="integrated", broker_type=False):
        result = {}
        for record in self.search(
            [
                ("integrated_webhook_state", "=", state),
                ("broker_type", "=", broker_type),
            ]
        ):
            result[record.webhook_key] = record._get_broker_data()
        return result

    def _get_broker_data(self):
        return {
            "id": self.id,
            "webhook_secret": self.webhook_secret,
            "webhook_user_id": self.webhook_user_id.id,
        }

    @api.model
    def _get_broker(self, key, state="integrated", broker_type=False, **kwargs):
        # We are using cache in order to avoid an exploit
        if not key:
            return False
        return self._get_broker_map(state=state, broker_type=broker_type).get(
            key, False
        )
