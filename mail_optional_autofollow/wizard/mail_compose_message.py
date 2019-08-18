# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def default_get(self, fields_list):
        res = super(MailComposeMessage, self).default_get(fields_list)
        res.setdefault(
            'autofollow_recipients',
            self.env.context.get('mail_post_autofollow', False))
        return res

    autofollow_recipients = fields.Boolean(
        string='Make recipients followers',
        help="""if checked, the additional recipients will be added as\
        followers on the related object""")

    @api.multi
    def send_mail(self, auto_commit=False):
        for wizard in self:
            super(MailComposeMessage, wizard.with_context(
                mail_post_autofollow=wizard.autofollow_recipients)).send_mail(
                    auto_commit=auto_commit)
        return True
