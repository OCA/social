# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    _mail_notification_include_history = False
