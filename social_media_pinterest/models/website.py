# -*- coding: utf-8 -*-
# © 2016 Diagram Software S.L.
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp import fields, models


class Website(models.Model):

    _inherit = 'website'

    social_pinterest = fields.Char('Pinterest Account')
