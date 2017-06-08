# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Javier Iniesta
# See README.rst file on addon root folder for more details

from openerp import models, fields


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    opt_out = fields.Boolean(
        string="Opt-Out", default=False,
        help="If opt-out is checked, this contact has refused to receive "
             "emails for mass mailing and marketing campaign.")
