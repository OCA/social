# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailFollowers(models.Model):
    _inherit = "mail.followers"

    @api.model
    def check_can_send_message(self):
        return self.user_has_groups(
            "mail_restrict_send_button.group_show_send_message_button"
        )
