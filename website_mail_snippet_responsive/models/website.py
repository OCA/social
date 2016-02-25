# -*- coding: utf-8 -*-
# (c) 2015 Antiun Ingeniería S.L. - Sergio Teruel
# (c) 2015 Antiun Ingeniería S.L. - Carlos Dauden
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.

from openerp import models, fields


class Website(models.Model):
    _inherit = 'website'

    mail_button_color = fields.Char(default='#00B518')
