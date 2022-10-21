# Copyright 2022 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import mimetypes
from datetime import datetime

import requests

from odoo import models


class MailBrokerChannel(models.Model):
    _inherit = "mail.broker.channel"

    def whatsapp_update(self, updates):
        self.ensure_one()
        body = ""
        attachments = []
        for entry in updates["entry"]:
            for change in entry["changes"]:
                if change["field"] != "messages":
                    continue
                for message in change["value"]["messages"]:
                    if message.get("text"):
                        body = message.get("text").get("body")
                    for key in ["image", "audio", "video"]:
                        if message.get(key):
                            image_id = message.get(key).get("id")
                            if image_id:
                                image_info_request = requests.get(
                                    "https://graph.facebook.com/v13.0/%s" % image_id,
                                    headers={
                                        "Authorization": "Bearer %s"
                                        % self.broker_id.token,
                                    },
                                )
                                image_info_request.raise_for_status()
                                image_info = image_info_request.json()
                                image_url = image_info["url"]
                            else:
                                image_url = message.get(key).get("url")
                            if not image_url:
                                continue
                            image_request = requests.get(
                                image_url,
                                headers={
                                    "Authorization": "Bearer %s" % self.broker_id.token,
                                },
                            )
                            image_request.raise_for_status()
                            attachments.append(
                                (
                                    "{}{}".format(
                                        image_id,
                                        mimetypes.guess_extension(
                                            image_info["mime_type"]
                                        ),
                                    ),
                                    base64.b64encode(image_request.content).decode(
                                        "utf-8"
                                    ),
                                    image_info["mime_type"],
                                )
                            )
                    if message.get("location"):
                        body += (
                            '<a target="_blank" href="https://www.google.com/'
                            'maps/search/?api=1&query=%s,%s">Location</a>'
                            % (
                                message["location"]["latitude"],
                                message["location"]["longitude"],
                            )
                        )
                    if message.get("contacts"):
                        pass
                    if len(body) > 0 or attachments:
                        self.message_post_broker(
                            body=body,
                            broker_type="whatsapp",
                            date=datetime.fromtimestamp(int(message["timestamp"])),
                            message_id=message.get("id"),
                            subtype="mt_comment",
                            attachments=attachments,
                        )
