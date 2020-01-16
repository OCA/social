# Copyright 2020 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    mail_group_id = fields.Many2one('mail.security.group', readonly=False)

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        result = super()._message_read_dict_postprocess(messages, message_tree)
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            message_dict['private'] = bool(message.mail_group_id)
            message_dict['mail_group_id'] = message.mail_group_id.id
            message_dict['mail_group'] = message.mail_group_id.name
        return result
