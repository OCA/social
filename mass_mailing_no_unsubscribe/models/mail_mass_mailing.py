# -*- coding: utf-8 -*-
# © 2015 ONESTEiN BV (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class MailMassMailing(models.Model):
    _inherit = 'mail.mass_mailing'

    allow_unsubscribe = fields.Boolean('Allow Unsubscribe')
