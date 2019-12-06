# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    notify_followers = fields.Boolean(default=True)

    def send_mail(self, auto_commit=False):
        for wizard in self:
            wizard = wizard.with_context(notify_followers=wizard.notify_followers)
            super(MailComposeMessage, wizard).send_mail(auto_commit=auto_commit)
        return True
