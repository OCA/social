# -*- coding: utf-8 -*-
# © 2016 Tecnativa S.L. - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class MailMassMailingTest(models.TransientModel):
    _inherit = 'mail.mass_mailing.test'

    mass_mailing_id = fields.Many2one(ondelete='cascade')
