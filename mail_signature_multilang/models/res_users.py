# -*- coding: utf-8 -*-
# See README.rst file on addon root folder for license details

from openerp import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    signature = fields.Html(translate=True)
