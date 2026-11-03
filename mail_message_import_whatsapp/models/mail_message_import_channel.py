# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MailMessageImportChannel(models.Model):
    """A WhatsApp number that receives messages, through a WhatsApp gateway."""

    _inherit = "mail.message.import.channel"

    channel_type = fields.Selection(selection_add=[("whatsapp", "WhatsApp")])
    gateway_id = fields.Many2one(
        "mail.gateway",
        string="Gateway",
        ondelete="restrict",
        check_company=True,
        domain="[('gateway_type', '=', 'whatsapp')]",
        help="WhatsApp gateway that receives the webhooks of Meta.",
    )
    phone_number_id = fields.Char(
        string="Meta Phone Number ID",
        help="Identifier of the number in Meta (WhatsApp Manager > API setup). "
        "Meta sends it with every message as metadata.phone_number_id.",
    )
    display_phone_number = fields.Char(
        string="Phone Number",
        help="Number the senders write or forward their messages to, e.g. "
        "+34 600 000 000.",
    )
    whatsapp_account_id = fields.Char(
        string="WhatsApp Business Account ID",
        related="gateway_id.whatsapp_account_id",
    )
    webhook_url = fields.Char(related="gateway_id.webhook_url")

    _sql_constraints = [
        (
            "phone_number_uniq",
            "unique(gateway_id, phone_number_id)",
            "This Meta number is already configured for this gateway.",
        ),
    ]

    @api.constrains("channel_type", "gateway_id", "phone_number_id")
    def _check_whatsapp(self):
        for channel in self.filtered(lambda c: c.channel_type == "whatsapp"):
            if not channel.gateway_id or not channel.phone_number_id:
                raise ValidationError(
                    self.env._(
                        "A WhatsApp number needs its gateway and the phone "
                        "number ID of Meta."
                    )
                )

    @api.onchange("gateway_id")
    def _onchange_gateway_id(self):
        if self.gateway_id and not self.phone_number_id:
            self.phone_number_id = self.gateway_id.whatsapp_from_phone

    @api.depends(
        "phone_number_id",
        "gateway_id.integrated_webhook_state",
        "gateway_id.webhook_secret",
        "gateway_id.whatsapp_security_key",
        "gateway_id.token",
        "gateway_id.webhook_key",
    )
    def _compute_state(self):
        return super()._compute_state()

    def _channel_state(self):
        if self.channel_type != "whatsapp":
            return super()._channel_state()
        # Only the presence of the secrets is read, never their values.
        gateway = self.gateway_id.sudo()
        missing = [
            label
            for label, value in (
                (self.env._("access token"), gateway.token),
                (self.env._("app secret (webhook secret)"), gateway.webhook_secret),
                (self.env._("verify token"), gateway.whatsapp_security_key),
                (self.env._("webhook key"), gateway.webhook_key),
                (self.env._("phone number ID"), self.phone_number_id),
            )
            if not value
        ]
        if missing:
            return "not_configured", self.env._(
                "Missing: %(fields)s.", fields=", ".join(missing)
            )
        if gateway.integrated_webhook_state != "integrated":
            return "pending", self.env._(
                "Set the webhook of the gateway and verify it from Meta."
            )
        return "connected", False

    @api.model
    def _find_for_update(self, gateway, value):
        """The receiving channel of an incoming webhook, from its gateway and
        number."""
        phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
        channels = self.sudo().search(
            [("channel_type", "=", "whatsapp"), ("gateway_id", "=", gateway.id)]
        )
        channel = channels.filtered(lambda c: c.phone_number_id == str(phone_number_id))
        if not channel and not phone_number_id:
            channel = channels.filtered(
                lambda c: c.phone_number_id == gateway.whatsapp_from_phone
            )
        return channel[:1]

    def action_open_gateway(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.gateway",
            "res_id": self.gateway_id.id,
            "view_mode": "form",
        }
