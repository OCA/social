# -*- coding: utf-8 -*-
# © 2016 ONESTEiN BV (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    _defaults = {
        'opt_out': True,
    }
