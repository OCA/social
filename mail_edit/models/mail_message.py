# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMessage(models.Model):

    _inherit = 'mail.message'

    edited = fields.Boolean(
        compute='_compute_edited', store=True,
    )
    edited_message_ids = fields.One2many(
        comodel_name='mail.message.edition',
        inverse_name='parent_id',
        readonly=True,
    )

    @api.depends('edited_message_ids')
    def _compute_edited(self):
        for record in self:
            record.edited = bool(record.edited_message_ids)

    @api.model
    def _message_read_dict_postprocess(self, messages, message_tree):
        res = super()._message_read_dict_postprocess(messages, message_tree)
        mail_message_ids = {m.get('id') for m in messages if m.get('id')}
        mail_messages = self.browse(mail_message_ids)
        edited = {
            message.id: int(message.edited) for message in mail_messages
        }
        for message_dict in messages:
            mail_message_id = message_dict.get('id', False)
            if mail_message_id:
                message_dict['edited'] = edited[mail_message_id]
        return res


class MailMessageEdition(models.Model):

    _name = 'mail.message.edition'
    _order = 'create_date desc'

    parent_id = fields.Many2one(
        comodel_name='mail.message'
    )
    body = fields.Html(string='Body', readonly=True)
    create_date = fields.Datetime(string='Edited On', readonly=True)
