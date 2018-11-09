# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, _
from odoo.exceptions import ValidationError


class MassMailingContactListRel(models.Model):
    _inherit = 'mail.mass_mailing.list_contact_rel'

    @api.constrains('contact_id', 'list_id')
    def _check_contact_id_partner_id_list_id(self):
        for rel in self:
            if rel.contact_id.partner_id:
                contacts = rel.list_id.contact_ids - rel.contact_id
                if rel.contact_id.partner_id in contacts.mapped('partner_id'):
                    raise ValidationError(_("A partner cannot be multiple "
                                            "times in the same list"))
