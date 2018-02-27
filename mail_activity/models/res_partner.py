# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import models


class ResPartner(models.Model):
    _inherit = ['res.partner', 'mail.activity.mixin']
    _name = 'res.partner'
