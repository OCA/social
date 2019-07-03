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
        for record in self:
            messages = record.message_ids.filtered('email_cc')
            for msg in messages:
                email_cc_list = email_split_and_format(msg.email_cc)
                for cc in email_cc_list:
                    email_parts = getaddresses([cc])[0]
                    partner_id = record.message_partner_info_from_emails(
                        [email_parts[1]])[0].get('partner_id')
                    if not partner_id:
                        res[record.id].append((False, cc, _('Cc')))
                    else:
                        partner = ResPartnerObj.browse(partner_id,
                                                       self._prefetch)
                        record._message_add_suggested_recipient(
                            res, partner=partner, reason=_('Cc'))
        return res
