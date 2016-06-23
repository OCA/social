# -*- coding: utf-8 -*-
# © 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import fields, models


class MailMessageSubtype(models.Model):
    _inherit = 'mail.message.subtype'

    template_id = fields.Many2one(
        'email.template', string='Notification template',
        domain=[('model_id.model', '=', 'mail.notification')],
        help='This template will be used to render notifications sent out '
        'for this subtype')
