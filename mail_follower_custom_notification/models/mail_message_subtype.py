# -*- coding: utf-8 -*-
# © 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import fields, models


class MailMessageSubtype(models.Model):
    _inherit = 'mail.message.subtype'

    custom_notification_mail = fields.Selection(
        [('force_yes', 'Force yes'), ('force_no', 'Force no')],
        string='Send mail notification', help='Leave empty to use the '
        'on the partner\'s form, set to "Force yes" to always send messages '
        'of this type via email, and "Force no" to never send messages of '
        'type via email')
    custom_notification_own = fields.Boolean(
        'Notify about own messages', help='Check this to have notifications '
        'generated and sent via email about own messages')
    custom_notification_model_ids = fields.Many2many(
        'ir.model', string='Models', help='Choose for which models the '
        'custom configuration applies. This is only necessary if your subtype '
        'doesn\'t set a model itself', domain=[('osv_memory', '=', False)])
