# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Therp BV <http://therp.nl>
# Copyright 2018 Eficent <http://www.eficent.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from openerp import fields, models


class MailMessage(models.Model):
    _inherit = 'mail.message'

    mail_activity_type_id = fields.Many2one(
        'mail.activity.type', 'Mail Activity Type', index=True,
        ondelete='set null',
    )
