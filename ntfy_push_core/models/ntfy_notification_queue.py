# Copyright 2026 nurefexc (https://nurefexc.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class NtfyNotificationQueue(models.Model):
    _name = "ntfy.notification.queue"
    _description = "ntfy Queue"
    _order = "create_date desc"

    res_user_id = fields.Many2one("res.users", string="Recipient", required=True, ondelete="cascade")
    title = fields.Char(string="Title", required=True)
    body = fields.Text(string="Body")
    click_url = fields.Char(string="Action URL")
    state = fields.Selection([
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("error", "Error")
    ], default="pending", index=True)
    error_log = fields.Text(string="Error Log", readonly=True)

    @api.model
    def cron_process_ntfy_queue(self, batch_limit=100):
        """ Processes queue with high priority """
        records = self.search([("state", "in", ["pending", "error"])], limit=batch_limit)

        for record in records:
            user = record.res_user_id
            if not user.ntfy_topic_url:
                continue

            headers = {
                "Title": record.title.encode("utf-8"),
                "Priority": "4",
                "Tags": "odoo,bell",
                "Click": record.click_url
            }

            try:
                response = requests.post(
                    user.ntfy_topic_url,
                    data=record.body.encode("utf-8"),
                    headers=headers,
                    timeout=5
                )
                if response.status_code == 200:
                    record.state = "sent"
                else:
                    record.write({"state": "error", "error_log": f"HTTP {response.status_code}"})
            except Exception as e:
                record.write({"state": "error", "error_log": str(e)})
