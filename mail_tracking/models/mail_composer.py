# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    hide_followers = fields.Boolean(string="Hide follower message",
                                    default=False)

    @api.multi
    def send_mail(self, auto_commit=False):
        """This method marks as reviewed the message when using the 'Retry'
           option in the mail_failed_message widget"""
        message = self.env['mail.message'].browse(
            self._context.get('message_id'))
        if message.exists():
            message.mail_tracking_needs_action = False
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {
                    'type': 'failed_updated',
                    'id': message.id,
                    'status': message.mail_tracking_needs_action,
                })
        return super().send_mail(auto_commit=auto_commit)

    @api.model
    def get_record_data(self, values):
        """Overwrite 'partner_ids' if enable 'hide_followers' on mail
           composer"""
        values = super(MailComposer, self).get_record_data(values)
        # Only use selected partners without followers
        if self._context.get('default_hide_followers', False):
            values['partner_ids'] = [
                (6, 0, self._context.get('default_partner_ids', list()))
            ]
        return values
