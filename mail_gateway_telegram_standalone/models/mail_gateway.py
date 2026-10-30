import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    telegram_chat_ids = fields.One2many(
        "telegram.chat", "gateway_id", string="Authorized Chats"
    )

    def send_message(self, chat_id, message, parse_mode="HTML"):
        """Low-level method to send a raw message via Telegram API"""
        self.ensure_one()
        if self.gateway_type != "telegram":
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": parse_mode}
        try:
            with requests.Session() as session:
                response = session.post(url, json=payload, timeout=10)
                response.raise_for_status()
            return True
        except Exception as e:
            _logger.error("Telegram error for bot %s: %s", self.name, e)
            return False

    def action_test_connection(self):
        """Button to test connection to all registered simple chats"""
        self.ensure_one()
        if self.gateway_type != "telegram":
            return False

        if not self.telegram_chat_ids:
            raise UserError(_("Please add or fetch at least one Chat ID first."))

        for chat in self.telegram_chat_ids:
            msg = (
                _("<b>Success!</b> Connection from Odoo to <i>%s</i> is working.")
                % self.name
            )
            self.send_message(chat.chat_id, msg)

        return {
            "effect": {
                "fadeout": "slow",
                "message": _("Test messages sent!"),
                "type": "rainbow_man",
            }
        }

    def action_fetch_chats(self):
        """Automatically discovers Chat IDs of people who messaged the bot"""
        self.ensure_one()
        if self.gateway_type != "telegram":
            return False

        if self.webhook_key:
            raise UserError(
                _(
                    "Telegram does not allow fetching updates manually "
                    "while a Webhook is active. "
                    "Please disable the Webhook before using 'Fetch Chats'."
                )
            )

        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                return False

            for result in data.get("result", []):
                msg = result.get("message") or result.get("edited_message")
                if not msg:
                    continue

                chat_info = msg.get("chat")
                c_id = str(chat_info.get("id"))
                c_name = (
                    chat_info.get("username")
                    or chat_info.get("first_name")
                    or "Unknown"
                )

                if not self.telegram_chat_ids.filtered(
                    lambda c, c_id=c_id: c.chat_id == c_id
                ):
                    self.env["telegram.chat"].create(
                        {
                            "name": c_name,
                            "chat_id": c_id,
                            "gateway_id": self.id,
                        }
                    )
            return True
        except Exception as e:
            _logger.error("Fetch failed: %s", e)
            return False
