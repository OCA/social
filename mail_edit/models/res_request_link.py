# -*- coding: utf-8 -*-
# © 2016 Sunflower IT (http://sunflowerweb.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import fields, models


class ResRequestLink(models.Model):
    _inherit = "res.request.link"

    mail_edit = fields.Boolean(
        string="Mail move",
        default=True,
        index=True,
        help="Allow to move mails to this model.")
