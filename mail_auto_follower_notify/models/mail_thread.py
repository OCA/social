# -*- coding: utf-8 -*-
# Copyright 2017 Eficent Business and IT Consulting Services S.L.
#   (http://www.eficent.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openerp import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def _message_auto_subscribe_notify(self, partner_ids):
        """This is added in order to send an email notification to new
        followers that are system users (i.e. it won't send emails to
        customers)."""
        super(MailThread, self)._message_auto_subscribe_notify(partner_ids)
        if not partner_ids:
            return
        for record_id in self.ids:
            messages = self.env['mail.message'].sudo().search([
                ('model', '=', self._name),
                ('res_id', '=', record_id),
                ('subtype_id', '!=', False),
                ('subtype_id.internal', '=', False)], limit=1)
            if messages:
                self.env['res.partner'].browse(partner_ids)._notify(
                    messages, force_send=True)
