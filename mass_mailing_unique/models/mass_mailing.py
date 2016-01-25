# -*- coding: utf-8 -*-
# © 2015 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models


class MailMassMailingContact(models.Model):
    _inherit = "mail.mass_mailing.contact"
    _sql_constraints = [
        ("unique_mail_per_list", "UNIQUE(list_id, email)",
         "Cannot have the same email more than once in the same list.")
    ]


class MailMassMailingList(models.Model):
    _inherit = "mail.mass_mailing.list"
    _sql_constraints = [
        ("unique_name", "UNIQUE(name)",
         "Cannot have more than one lists with the same name.")
    ]
