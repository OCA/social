# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailingContact(models.Model):
    _inherit = "mailing.contact"

    partner_ids = fields.One2many(
        "res.partner",
        "mailing_contact_id",
        string="Partners",
        readonly=True,
    )
    partner_count = fields.Integer(
        string="Partners Count",
        compute="_compute_partner_count",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # Try to relate partners with the same email.
        records = super().create(vals_list)
        records._recompute_partner_relation()
        return records

    def write(self, vals):
        # If email is updated, it may render the partner relations outdated.
        # Recompute all partners with prev and current email.
        if "email" in vals:
            prev_emails = [rec.email_normalized for rec in self]
        res = super().write(vals)
        if "email" in vals:
            self._recompute_partner_relation(include_emails=prev_emails)
        return res

    def _recompute_partner_relation(self, include_emails=None):
        """Recomputes partner mailing_contact_id relation

        Our relation is based on the email field, not a real FK.

        In case new records are created, or their emails are updated,
        we need to also update the related partners relations.
        """
        emails = self.mapped("email_normalized")
        if include_emails:
            emails += include_emails
        # Make sure they're unique
        emails = list(set(emails))
        if not emails:  # pragma: no cover
            return
        partners = self.env["res.partner"].search([("email_normalized", "in", emails)])
        partners._compute_mailing_contact_id()

    @api.depends("partner_ids")
    def _compute_partner_count(self):
        results = self.env["res.partner"].read_group(
            [("mailing_contact_id", "in", self.ids)],
            fields=["mailing_contact_id"],
            groupby=["mailing_contact_id"],
        )
        count_map = {
            x["mailing_contact_id"][0]: x["mailing_contact_id_count"] for x in results
        }
        for rec in self:
            rec.partner_count = count_map.get(rec.id, 0)

    def action_view_partner_ids(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_partner_form")
        action["domain"] = [("mailing_contact_id", "in", self.ids)]
        action["context"] = False
        return action
