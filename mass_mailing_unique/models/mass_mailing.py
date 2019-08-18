# Copyright 2015 Grupo ESOC Ingeniería de Servicios, S.L.U. - Jairo Llopis
# Copyright 2016 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import models, api, _, tools
from odoo.exceptions import ValidationError


class MailMassMailingContact(models.Model):
    _inherit = "mail.mass_mailing.contact"

    @api.constrains('email', 'list_ids')
    def _check_email_list_ids(self):
        for contact in self:
            other_contact = self.search([
                ('email', '=ilike', tools.escape_psql(contact.email)),
                ('id', '!=', contact.id)
            ])
            if contact.list_ids & other_contact.mapped('list_ids'):
                raise ValidationError(_("Cannot have the same email more "
                                        "than once in the same list"))


class MailMassMailingList(models.Model):
    _inherit = "mail.mass_mailing.list"
    _sql_constraints = [
        ("unique_name", "UNIQUE(name)",
         "Cannot have more than one lists with the same name.")
    ]
