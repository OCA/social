# Copyright 2015 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# Copyright 2016 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailMassMailingList(models.Model):
    _inherit = "mail.mass_mailing.list"

    _sql_constraints = [
        ("unique_name", "UNIQUE(name)",
         "Cannot have more than one lists with the same name.")
    ]
