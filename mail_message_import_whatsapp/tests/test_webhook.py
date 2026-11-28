# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import hmac
import json

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from .common import MailMessageImportWhatsappCase


@tagged("post_install", "-at_install")
class TestWebhook(MailMessageImportWhatsappCase, HttpCase):
    """The webhooks go through the controller of the gateway, signature
    included."""

    def _post(self, payload, signature=True, secret=None):
        data = json.dumps(payload)
        headers = {"Content-Type": "application/json"}
        if signature:
            digest = hmac.new(
                (secret or "meta-app-secret").encode(), data.encode(), hashlib.sha256
            ).hexdigest()
            headers["x-hub-signature-256"] = f"sha256={digest}"
        return self.url_open(
            f"/gateway/whatsapp/{self.gateway.webhook_key}/update",
            data=data,
            headers=headers,
        )

    def _messages(self):
        return self.env["mail.message.import.message"].search(
            [("channel_id", "=", self.whatsapp_channel.id)]
        )

    def test_signed_message_is_received(self):
        response = self._post(self._payload(text="Hola, adjunto presupuesto"))
        self.assertEqual(response.status_code, 200)
        message = self._messages()
        self.assertEqual(len(message), 1)
        self.assertEqual(message.sender_id, self.sender)
        self.assertEqual(message.state, "queued")
        self.assertEqual(message.body, "Hola, adjunto presupuesto")
        self.assertEqual(message.sender_name, "Ana")
        self.assertTrue(message.mail_message_id)
        self.assertEqual(message.discuss_channel_id.gateway_id, self.gateway)
        self.assertEqual(message.conversation_id.state, "open")

    @mute_logger("odoo.addons.mail_gateway.controllers.gateway")
    def test_unsigned_message_is_rejected(self):
        self._post(self._payload(text="Sin firma"), signature=False)
        self.assertFalse(self._messages())

    @mute_logger("odoo.addons.mail_gateway.controllers.gateway")
    def test_wrong_signature_is_rejected(self):
        self._post(self._payload(text="Firma falsa"), secret="another-secret")
        self.assertFalse(self._messages())

    @mute_logger(
        "odoo.addons.mail_message_import_whatsapp.models.mail_gateway_whatsapp"
    )
    def test_redelivery_is_ignored(self):
        payload = self._payload(text="Mensaje repetido por Meta")
        self._post(payload)
        self._post(payload)
        message = self._messages()
        self.assertEqual(len(message), 1)
        posted = self.env["mail.message"].search(
            [
                ("model", "=", "discuss.channel"),
                ("res_id", "=", message.discuss_channel_id.id),
                ("message_type", "=", "comment"),
            ]
        )
        self.assertEqual(len(posted), 1, "The gateway must not post it twice")
