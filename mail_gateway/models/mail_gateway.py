# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools


class MailGateway(models.Model):
    _name = "mail.gateway"
    _description = "Mail Gateway"

    name = fields.Char(required=True)
    token = fields.Char(required=True, help="Key used for integration purposes")
    gateway_type = fields.Selection([], required=True)
    webhook_key = fields.Char(help="Key used on the connection URL")
    webhook_secret = fields.Char(
        help="""Key used to ensure that the connection is secure and
        comes from the desired source"""
    )
    integrated_webhook_state = fields.Selection(
        [("pending", "Pending"), ("integrated", "Integrated")], readonly=True
    )
    can_set_webhook = fields.Boolean(compute="_compute_webhook_checks")
    webhook_url = fields.Char(compute="_compute_webhook_url")
    has_new_channel_security = fields.Boolean(
        help="When checked, channels are not created automatically. Usable on Telegram"
    )
    webhook_user_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.ref("base.user_root"),
        help="User that will create the messages",
    )
    member_ids = fields.Many2many("res.users")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company.id
    )

    _sql_constraints = [
        ("mail_gateway_token", "unique(token)", "Token must be unique"),
        (
            "mail_gateway_webhook_key",
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
            self.env["discuss.channel"]
            .search(
                [
                    ("gateway_channel_token", "=", str(chat_token)),
                    ("gateway_id", "=", self.id),
                ],
                limit=1,
            )
            .id
        )

    def _get_webhook_url(self):
        return "{}/gateway/{}/{}/update".format(
            self.webhook_url
            or self.env["ir.config_parameter"].get_param("web.base.url"),
            self.gateway_type,
            self.webhook_key,
        )

    def _can_set_webhook(self):
        return self.webhook_key and self.webhook_user_id

    @api.depends("gateway_type")
    def _compute_webhook_checks(self):
        for record in self:
            record.can_set_webhook = record._can_set_webhook()

    def set_webhook(self):
        self.ensure_one()
        if self.can_set_webhook:
            self.env[f"mail.gateway.{self.gateway_type}"]._set_webhook(self)

    def remove_webhook(self):
        self.ensure_one()
        self.env[f"mail.gateway.{self.gateway_type}"]._remove_webhook(self)

    def update_webhook(self):
        self.ensure_one()
        self.remove_webhook()
        self.set_webhook()

    def write(self, vals):
        res = super().write(vals)
        if (
            "webhook_key" in vals
            or "integrated_webhook_state" in vals
            or "webhook_secret" in vals
            or "webhook_user_id" in vals
        ):
            self.env.registry.clear_cache()
        return res

    @api.model_create_multi
    def create(self, mvals):
        res = super().create(mvals)
        self.env.registry.clear_cache()
        return res

    @api.model
    @tools.ormcache()
    def _get_gateway_map(self, state="integrated", gateway_type=False):
        result = {}
        for record in self.sudo().search(
            [
                ("integrated_webhook_state", "=", state),
                ("gateway_type", "=", gateway_type),
            ]
        ):
            result[record.webhook_key] = record._get_gateway_data()
        return result

    def _get_gateway_data(self):
        return {
            "id": self.id,
            "company_id": self.company_id.id,
            "webhook_secret": self.webhook_secret,
            "webhook_user_id": self.webhook_user_id.id,
        }

    @api.model
    def _get_gateway(self, key, state="integrated", gateway_type=False):
        # We are using cache in order to avoid an exploit
        if not key:
            return False
        return self._get_gateway_map(state=state, gateway_type=gateway_type).get(
            key, False
        )

    def gateway_info(self):
        return [record._gateway_info() for record in self]

    def _gateway_info(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.gateway_type,
        }
