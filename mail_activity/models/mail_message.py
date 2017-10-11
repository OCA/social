# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    mail_activity_type_id = fields.Many2one(
        'mail.activity.type', 'Mail Activity Type', index=True,
        ondelete='set null',
    )
