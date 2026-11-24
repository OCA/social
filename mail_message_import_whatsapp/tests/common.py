# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import copy
import itertools
from contextlib import contextmanager
from unittest.mock import patch

from odoo import fields

from odoo.addons.mail_message_import.tests.common import MailMessageImportCase

CLIENT_PHONE = "34600111222"
WAMIDS = itertools.count(1)


class MailMessageImportWhatsappCase(MailMessageImportCase):
    """The shared data, received by WhatsApp: Meta is mocked and the messages
    reach the gateway as its webhooks."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gateway = cls.env["mail.gateway"].create(
            {
                "name": "Orders WhatsApp",
                "gateway_type": "whatsapp",
                "token": "meta-token",
                "webhook_key": "wa-hook",
                "webhook_secret": "meta-app-secret",
                "whatsapp_security_key": "verify-token",
                "whatsapp_from_phone": "1099",
            }
        )
        cls.gateway.integrated_webhook_state = "integrated"
        cls.whatsapp_channel = cls.env["mail.message.import.channel"].create(
            {
                "name": "Orders WhatsApp",
                "channel_type": "whatsapp",
                "gateway_id": cls.gateway.id,
                "phone_number_id": "1099",
                "display_phone_number": "+34 900 000 000",
            }
        )
        cls.env["mail.message.import.address"].create(
            {
                "sender_id": cls.sender.id,
                "channel_type": "whatsapp",
                "address": f"+{CLIENT_PHONE}",
                "name": "Buyer",
            }
        )

    # ------------------------------------------------------------------
    # Meta
    # ------------------------------------------------------------------

    def _payload(self, sender=CLIENT_PHONE, wamid=None, text=None, **message):
        wamid = wamid or f"wamid.TEST{next(WAMIDS)}"
        content = {
            "from": sender,
            "id": wamid,
            "timestamp": str(int(fields.Datetime.now().timestamp())),
            "type": "text",
        }
        if text is not None:
            content["text"] = {"body": text}
        content.update(message)
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "34900000000",
                                    "phone_number_id": "1099",
                                },
                                "contacts": [
                                    {"profile": {"name": "Ana"}, "wa_id": sender}
                                ],
                                "messages": [content],
                            },
                        }
                    ],
                }
            ],
        }

    def _deliver(self, payload):
        """Hand a webhook to the gateway, as its controller does after the
        signature."""
        # As the controller: nothing is sent back to Meta.
        service = self.env["mail.gateway.whatsapp"].with_context(
            no_gateway_notification=True
        )
        gateway = service.env["mail.gateway"].browse(self.gateway.id)
        service._receive_update(gateway, copy.deepcopy(payload))
        wamid = payload["entry"][0]["changes"][0]["value"]["messages"][0]["id"]
        return self.env["mail.message.import.message"].search(
            [("message_uid", "=", wamid)]
        )

    def _receive(self, text=None, **kwargs):
        return self._deliver(self._payload(text=text, **kwargs))

    @contextmanager
    def _media(self, content, mime_type):
        """Meta answers the downloads of the gateway with ``content``."""

        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {"url": "https://media.example/file", "mime_type": mime_type}

        response = Response()
        response.content = content
        with patch(
            "odoo.addons.mail_gateway_whatsapp.models.mail_gateway_whatsapp."
            "requests.get",
            return_value=response,
        ):
            yield
