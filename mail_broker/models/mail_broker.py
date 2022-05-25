# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, tools


class MailBroker(models.Model):
    _name = "mail.broker"
    _description = "Mail Broker"

    name = fields.Char(required=True)
    token = fields.Char(required=True)
    broker_type = fields.Selection([], required=True)
    show_on_app = fields.Boolean(default=True)
    webhook_key = fields.Char()
    integrated_webhook = fields.Boolean(readonly=True)
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

    def _get_webhook_url(self):
        return "%s/broker/%s/update" % (
            self.webhook_url
            or self.env["ir.config_parameter"].get_param("web.base.url"),
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
            self._set_webhook()

    def remove_webhook(self):
        self.ensure_one()
        self._remove_webhook()

    def update_webhook(self):
        self.ensure_one()
        self.remove_webhook()
        self.set_webhook()

    def _set_webhook(self):
        self.integrated_webhook = True

    def _remove_webhook(self):
        self.integrated_webhook = False

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

    def _receive_update(self, update):
        return getattr(self, "_receive_update_%s" % self.broker_type)(update)

    def write(self, vals):
        res = super(MailBroker, self).write(vals)
        if "webhook_key" in vals:
            self.clear_caches()
        return res

    @api.model_create_single
    def create(self, vals):
        res = super(MailBroker, self).create(vals)
        if "webhook_key" in vals:
            self.clear_caches()
        return res

    @api.model
    @tools.ormcache()
    def _get_broker_map(self):
        result = {}
        for record in self.search([]):
            result[record.webhook_key] = record.id
        return result

    @api.model
    def _get_broker_id(self, key):
        # We are using cache in order to avoid an exploit
        if not key:
            return False
        return self._get_broker_map().get(key, False)

    def _get_channel_id(self, chat_token):
        return (
            self.env["mail.broker.channel"]
            .search(
                [("token", "=", str(chat_token)), ("broker_id", "=", self.id)], limit=1
            )
            .id
        )

    def _get_channel(self, token, update, force_create=False):
        chat_id = self._get_channel_id(token)
        if chat_id:
            return self.env["mail.broker.channel"].browse(chat_id)
        if not force_create and self.has_new_channel_security:
            return False
        return self.env["mail.broker.channel"].create(
            self._get_channel_vals(token, update)
        )

    def _get_channel_vals(self, token, update):
        return {
            "token": token,
            "broker_id": self.id,
            "show_on_app": self.show_on_app,
        }
