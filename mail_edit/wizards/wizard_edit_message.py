# Copyright 2019 Creu Blanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WizardEditMessage(models.TransientModel):

    _name = 'wizard.edit.message'

    name = fields.Char()
    message = fields.Html()
    old_message = fields.Html()
    mail_message_id = fields.Many2one(
        comodel_name='mail.message',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        message_id = self.env.context.get('mail_message_id', False)
        if not message_id:
            raise ValidationError(_('Message not found'))
        res['mail_message_id'] = message_id
        message_id = self.env['mail.message'].browse(message_id)
        res['message'] = message_id.body
        res['old_message'] = message_id.body
        return res

    @api.multi
    def save_message_changes(self):
        if self.message != self.old_message:
            self.mail_message_id.write({
                'body': self.message,
                'edited_message_ids': [(0, 0, {'body': self.old_message})]
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return {'type': 'ir.actions.act_window_close'}
