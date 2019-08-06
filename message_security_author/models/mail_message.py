# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models, _
from odoo.exceptions import AccessError


class Message(models.Model):
    _inherit = 'mail.message'

    @api.multi
    def write(self, vals):
        user = self.env.user
        if self._uid == 1:
            rec = super(Message, self).write(vals=vals)
        elif self._name != 'mail.message':
            rec = super(Message, self).write(vals=vals)
        elif user.has_group(
                'message_security_author.group_mail_message_manager'):
            rec = super(Message, self).write(vals=vals)
        elif not self.filtered(lambda m: user not in m.author_id.user_ids):
            rec = super(Message, self).write(vals=vals)
        elif self.model == 'crm.lead' and vals.get('subject') and \
                vals.get('res_id'):
            rec = super(Message, self).write(vals=vals)
        else:
            raise AccessError(
                _("Sorry, you are not allowed to modify this document."))
        return rec

    @api.multi
    def unlink(self):
        user = self.env.user
        if self._uid == 1:
            rec = super(Message, self).unlink()
        elif self._name != 'mail.message':
            rec = super(Message, self).unlink()
        elif self._context.get('deleting_mail_thread'):
            rec = super(Message, self).unlink()
        elif user.has_group(
                'message_security_author.group_mail_message_manager'):
            rec = super(Message, self).unlink()
        elif not self.filtered(lambda m: user not in m.author_id.user_ids):
            rec = super(Message, self).unlink()
        else:
            raise AccessError(
                _("Sorry, you are not allowed to delete this document."))
        return rec
