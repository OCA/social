# -*- coding: utf-8 -*-
# © 2014-2015 Grupo ESOC <www.grupoesoc.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import fields, models


class ResRequestLink(models.Model):
    _inherit = "res.request.link"

    mail_forward_target = fields.Boolean(
        default=True,
        index=True,
        help="Allow to forward mails to this model.")
