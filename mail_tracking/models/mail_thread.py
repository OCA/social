# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, _
from email.utils import getaddresses
from odoo.tools import email_split_and_format


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, *args, **kwargs):
        new_message = super().message_post(*args, **kwargs)
        email_cc = kwargs.get('cc')
        if email_cc:
            new_message.sudo().write({
                'email_cc': email_cc,
            })
        return new_message

    @api.multi
    def message_get_suggested_recipients(self):
        res = super().message_get_suggested_recipients()
        ResPartnerObj = self.env['res.partner']
        email_cc_formated_list = []
        for record in self:
            emails_cc = record.message_ids.mapped('email_cc')
            for email in emails_cc:
                email_cc_formated_list.extend(email_split_and_format(email))
        email_cc_formated_list = set(email_cc_formated_list)
        for cc in email_cc_formated_list:
            email_parts = getaddresses([cc])[0]
            partner_id = record.message_partner_info_from_emails(
                [email_parts[1]])[0].get('partner_id')
            if not partner_id:
                record._message_add_suggested_recipient(
                    res, email=cc, reason=_('Cc'))
            else:
                partner = ResPartnerObj.browse(partner_id, self._prefetch)
                record._message_add_suggested_recipient(
                    res, partner=partner, reason=_('Cc'))
        return res
