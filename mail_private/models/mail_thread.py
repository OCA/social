# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from lxml import etree
from odoo import api, fields, models
from odoo.osv.orm import setup_modifiers


class MailThread(models.AbstractModel):

    _inherit = 'mail.thread'

    allow_private = fields.Boolean(
        compute='_compute_allow_private',
    )

    def _compute_allow_private(self):
        groups = self.env['mail.security.group'].search([
            ('model_ids.model', '=', self._name),
            ])
        users = groups.mapped('group_ids.users')
        for record in self:
            record.allow_private = groups and self.env.user in users

    @api.model
    def get_message_security_groups(self):
        return self.env['mail.security.group'].search([
            ('model_ids.model', '=', self._name),
            ('group_ids.users', '=', self.env.user.id)
        ])._get_security_groups()

    @api.model
    def fields_view_get(
        self, view_id=None, view_type="form", toolbar=False, submenu=False
    ):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='message_ids']/.."):
                element = etree.Element(
                    'field',
                    attrib={
                        "name": "allow_private",
                        "invisible": "1",
                    }
                )
                setup_modifiers(element)
                node.insert(0, element)
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _message_post_process_attachments(
        self, attachments, attachment_ids, message_data
    ):
        if attachment_ids and self.env.context.get('default_mail_group_id'):
            filtered_attachment_ids = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'mail.compose.message'),
                ('create_uid', '=', self._uid),
                ('id', 'in', attachment_ids),
            ])
            filtered_attachment_ids.write({
                'mail_group_id': self.env.context.get('default_mail_group_id'),
            })
        return super()._message_post_process_attachments(
            attachments, attachment_ids, message_data)

    def message_get_message_notify_values(self, message, message_values):
        if hasattr(super(), 'message_get_message_notify_values'):
            message_vals = super().message_get_message_notify_values(
                message, message_values)
        else:
            message_vals = message_values.copy()
        if not message.mail_group_id:
            return message_vals
        partner_obj = self.env['res.partner']
        accepted_users = message.mail_group_id.mapped(
            'group_ids.users')
        new_partners = partner_obj.browse()
        for act, ext, pids in message_values.get('needaction_partner_ids', []):
            if act != 6:
                continue
            partners = partner_obj.browse(pids)
            for partner in partners:
                if partner.user_ids in accepted_users:
                    new_partners |= partner
        new_vals = {}
        if new_partners:
            new_vals['needaction_partner_ids'] = [(6, 0, new_partners.ids)]
        return new_vals
