# -*- coding: utf-8 -*-
# (c) 2015 Serv. Tecnol. Avanzados - Pedro M. Baeza
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import models


class ResPartner(models.Model):
    """This is for avoid inheritance problem:
    https://github.com/odoo/odoo/issues/9084"""
    _name = 'res.partner'
    _inherit = ['mail.thread', 'res.partner']
