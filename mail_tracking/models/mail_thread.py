# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api, _
from email.utils import getaddresses
from odoo.tools import email_split_and_format
from lxml import etree
import logging
_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, body='', subject=None, message_type='notification',
                     subtype=None, parent_id=False, attachments=None,
                     content_subtype='html', **kwargs):
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

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        """Add a filter to any model with mail.thread that will show up records
           with tracking errors.
        """
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar,
            submenu=submenu)
        if view_type != 'search':
            return res

        # Create filter element
        filter_name = "message_ids_with_tracking_errors"
        tracking_error_domain = """[
            ("message_ids.mail_tracking_ids.state", "in",
                ['error', 'rejected', 'spam', 'bounced', 'soft-bounced']),
            ("message_ids.track_needs_action", "=", True)]"""
        new_filter = etree.Element(
            'filter', {
                'string': _('Messages with errors'),
                'name': filter_name,
                'domain': tracking_error_domain})
        separator = etree.Element('separator', {})
        new_filter.append(separator)

        # Modify view to add new filter element
        doc = etree.XML(res['arch'])
        node = doc.xpath("//search")[0]
        node.insert(0, new_filter)
        res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
