# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WizardViewPreviousEditions(models.TransientModel):

    _name = 'wizard.view.previous.editions'

    name = fields.Char()
    mail_message_id = fields.Many2one(
        comodel_name='mail.message',
    )
    edited_message_ids = fields.Many2many(
        comodel_name='mail.message.edition',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        message_id = self.env.context.get('mail_message_id', False)
        if not message_id:
            raise ValidationError(_('Message not found'))
        res['mail_message_id'] = message_id
        message_id = self.env['mail.message'].browse(message_id)
        if message_id:
            res['edited_message_ids'] = [
                (6, 0, message_id.edited_message_ids.ids)
            ]
        return res
