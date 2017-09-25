# -*- coding: utf-8 -*-
# © 2017 Phuc.nt - <phuc.nt@komit-consulting.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    split_mail_by_recipients = fields.Selection([
        ('split', 'One mail for each recipient'),
        ('merge', 'One mail for all recipients'),
        ('default', 'Project Default')],
        string='Split mail by recipient partner',
        default='default',
    )
