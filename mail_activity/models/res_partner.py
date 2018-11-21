# -*- coding: utf-8 -*-
# Copyright 2016 Odoo SA <https://www.odoo.com>
# Copyright 2018 Therp BV <http://therp.nl>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from openerp import models
from .mail_activity_mixin import setup_mail_actitivities


@setup_mail_actitivities
class ResPartner(models.Model):
    _inherit = 'res.partner'
