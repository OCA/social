# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, api, _
from email.utils import getaddresses
from odoo.tools import email_split_and_format
from lxml import etree


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    failed_message_ids = fields.One2many(
        'mail.message', 'res_id', string='Failed Messages',
        domain=lambda self:
            [('model', '=', self._name)]
            + self._get_failed_message_domain(),
        auto_join=True)

    def _get_failed_message_domain(self):
        """Domain used to display failed messages on the 'failed_messages'
           widget"""
        failed_states = self.env['mail.message'].get_failed_states()
        return [
            ('mail_tracking_needs_action', '=', True),
            ('mail_tracking_ids.state', 'in', list(failed_states)),
        ]

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, body='', subject=None, message_type='notification',
                     subtype=None, parent_id=False, attachments=None,
                     content_subtype='html', **kwargs):
        """Adds CC recipient to the message.

        Because Odoo implementation avoid store cc recipients we ensure that
        this information its written into the mail.message record.
        """
        new_message = super().message_post(
            body=body, subject=subject, message_type=message_type,
            subtype=subtype, parent_id=parent_id, attachments=attachments,
            content_subtype=content_subtype, **kwargs)
        email_cc = kwargs.get('cc')
        if email_cc:
            new_message.sudo().write({
                'email_cc': email_cc,
            })
        return new_message

    @api.multi
    def message_get_suggested_recipients(self):
        """Adds email Cc recipients as suggested recipients.
           If the recipient have an res.partner uses it."""
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

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                         submenu=False):
        """Add filters for failed messages.

        These filters will show up on any form or search views of any
        model inheriting from ``mail.thread``.
        """
        res = super()._fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        if view_type not in {'search', 'form'}:
            return res
        doc = etree.XML(res['arch'])
        if view_type == 'search':
            # Modify view to add new filter element
            nodes = doc.xpath("//search")
            if nodes:
                # Create filter element
                new_filter = etree.Element(
                    'filter', {
                        'string': _('Failed sent messages'),
                        'name': "failed_message_ids",
                        'domain': str([
                            ['failed_message_ids.mail_tracking_ids.state',
                             'in',
                             list(
                                 self.env['mail.message'].get_failed_states()
                             )],
                            ['failed_message_ids.mail_tracking_needs_action',
                             '=', True]
                        ])
                    })
                nodes[0].append(etree.Element('separator'))
                nodes[0].append(new_filter)
        elif view_type == 'form':
            # Modify view to add new field element
            nodes = doc.xpath(
                "//field[@name='message_ids' and @widget='mail_thread']")
            if nodes:
                # Create field
                field_failed_messages = etree.Element('field', {
                    'name': 'failed_message_ids',
                    'widget': 'mail_failed_message',
                })
                nodes[0].addprevious(field_failed_messages)
        res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
