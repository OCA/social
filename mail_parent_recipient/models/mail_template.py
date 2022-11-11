# Copyright 2018-2022 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class MailTemplate(models.Model):

    _inherit = "mail.template"

    def generate_recipients(self, results, res_ids):
        """Use partner's parent email as recipient.

        Walk up the hierarchy of recipient partners via `parent_id`
        and pick the 1st one having an email.
        """
        results = super().generate_recipients(results, res_ids)
        use_parent_address = (
            self.env["ir.config_parameter"].sudo().get_param("mail.use_parent_address")
        )
        disabled = self.env.context.get("no_parent_mail_recipient")
        if use_parent_address and not disabled:
            for res_id, values in results.items():
                partner_ids = values.get("partner_ids", [])
                partners_with_emails = []
                partners = self.env["res.partner"].sudo().browse(partner_ids)
                for partner in partners:
                    if partner.email:
                        partners_with_emails.append(partner.id)
                    elif partner.commercial_partner_id.email:
                        if partner.commercial_partner_id.id not in partners.ids:
                            partners_with_emails.append(
                                partner.commercial_partner_id.id
                            )
                results[res_id]["partner_ids"] = partners_with_emails
        return results
