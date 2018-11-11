# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailMassMailingList(models.Model):
    _inherit = 'mail.mass_mailing.list'

    @api.constrains('contact_ids')
    def _check_contact_ids_email(self):
        self.mapped("contact_ids")._check_email_list_ids()
