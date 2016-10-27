# -*- coding: utf-8 -*-
# © 2016 Diagram Software S.L.
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from openerp.models import Model
from openerp import fields


class Website(Model):

    _inherit = 'website'

    social_pinterest = fields.Char('Pinterest Account')
