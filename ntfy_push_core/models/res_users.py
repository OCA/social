# Copyright 2026 nurefexc (https://nurefexc.com)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

import hashlib
import time

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    notification_type = fields.Selection(
        selection_add=[("ntfy", "ntfy.sh (Push Notification)")],
        ondelete={"ntfy": "set default"},
    )

    ntfy_topic_url = fields.Char(
        string="ntfy Topic URL",
        readonly=True,
        copy=False,
        help="Paste this URL into your ntfy mobile app.",
    )
    ntfy_last_server_url = fields.Char(string="Last ntfy Server", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        for user in res:
            if user.notification_type == "ntfy" and not user.ntfy_topic_url:
                user.action_generate_ntfy_url()
        return res

    def write(self, vals):
        res = super().write(vals)
        # If switching to ntfy and no URL, or if something changed that requires it
        if "notification_type" in vals and vals["notification_type"] == "ntfy":
            for user in self:
                if not user.ntfy_topic_url:
                    user.action_generate_ntfy_url()
        return res

    def action_generate_ntfy_url(self):
        """Generates the secure SHA224 hashed topic URL"""
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        base_url = config.get_param("ntfy.server_url", "https://ntfy.sh").rstrip("/")
        db_uuid = config.get_param("database.uuid", "shared")

        seed = f"{db_uuid}-{self.id}-{time.time()}"
        secure_hash = hashlib.sha224(seed.encode()).hexdigest()
        topic_id = f"odoo-{self.id}-{secure_hash}"

        self.write(
            {
                "ntfy_topic_url": f"{base_url}/{topic_id}",
                "ntfy_last_server_url": base_url,
            }
        )

    def _check_ntfy_url_consistency(self):
        """Auto-sync when server config changes."""
        current_base = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("ntfy.server_url", "https://ntfy.sh")
            .rstrip("/")
        )
        for user in self:
            if user.notification_type == "ntfy":
                if not user.ntfy_topic_url or user.ntfy_last_server_url != current_base:
                    user.action_generate_ntfy_url()
