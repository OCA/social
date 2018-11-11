# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailMassMailingContactListRel(models.Model):
    _inherit = 'mail.mass_mailing.list_contact_rel'

    @api.constrains('contact_id', 'list_id')
    def _check_contact_id_partner_id_list_id(self):
        self.mapped("contact_id")._check_email_list_ids()
