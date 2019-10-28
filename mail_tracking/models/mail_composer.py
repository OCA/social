# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    hide_followers = fields.Boolean(string="Hide follower message",
                                    default=False)

    @api.multi
    def send_mail(self, auto_commit=False):
        """Make compatible with mail_failed_message widget.

        Mark as reviewed when using 'Retry' option in that widget.
        """
        message = self.env['mail.message'].browse(
            self._context.get('message_id'))
        if message.exists():
            message.mail_tracking_needs_action = False
        return super().send_mail(auto_commit=auto_commit)
