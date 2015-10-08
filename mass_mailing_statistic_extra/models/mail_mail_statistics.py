# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Antonio Espinosa
# See README.rst file on addon root folder for more details

from openerp import models, fields


class MailMailStatistics(models.Model):
    _inherit = 'mail.mail.statistics'

    email_from = fields.Char(string='From', readonly=True)
    email_to = fields.Char(string='To', readonly=True)
    subject = fields.Char(string='Subject', readonly=True)
