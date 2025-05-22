# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import UserError


class PartnerMailListWizard(models.TransientModel):
    _name = "partner.mail.list.wizard"
    _description = "Create contact mailing list"

    mail_list_id = fields.Many2one(comodel_name="mailing.list", string="Mailing List")
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="mail_list_wizard_partner",
        default=lambda self: self.env.context.get("active_ids"),
    )

    def add_to_mail_list(self):
        contact_obj = self.env["mailing.contact"]
        partners = self.partner_ids

        # Step 1: Existing contacts → add to mailing list if needed
        existing_partners = partners.filtered("mass_mailing_contact_ids")
        for partner in existing_partners:
            contact = partner.mass_mailing_contact_ids[0]
            subscribed_list_ids = contact.subscription_list_ids.list_id.ids
            if self.mail_list_id.id not in subscribed_list_ids:
                contact.write({
                    'subscription_list_ids': [(0, 0, {'list_id': self.mail_list_id.id})]
                })

        # Step 2: New contacts → let create() logic handle everything via default_list_ids
        new_partners = partners - existing_partners
        for partner in new_partners:
            if not partner.email:
                raise UserError(_("Partner '%s' has no email.") % partner.name)

            contact_vals = {
                "partner_id": partner.id,
                "title_id": partner.title.id if partner.title else False,
                "company_name": partner.company_id.name if partner.company_id else False,
                "country_id": partner.country_id.id if partner.country_id else False,
                "subscription_list_ids": [],  # triggers default_list_ids processing
            }

            # Pass default_list_ids in context
            contact_obj.with_context(default_list_ids=[self.mail_list_id.id]).create(contact_vals)
