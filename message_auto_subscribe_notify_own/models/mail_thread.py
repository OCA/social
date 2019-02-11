# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def message_auto_subscribe(self, updated_fields, values=None):
        super(MailThread, self).message_auto_subscribe(updated_fields,
                                                       values=values)
        user_field_lst = self._message_get_auto_subscribe_fields(
            updated_fields)
        to_add_users = self.env['res.users'].sudo().browse(
            [values[name] for name in user_field_lst if values.get(name)]
        ).filtered(lambda u: u.partner_id.active)
        user_pids = [user.partner_id.id for user in to_add_users
                     if user == self.env.user and
                     user.notification_type == 'email']
        if user_pids:
            self._message_auto_subscribe_notify(user_pids)
        return True
