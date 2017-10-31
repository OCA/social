# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo.tools import safe_eval


class MassMailingList(models.Model):
    _inherit = "mail.mass_mailing.list"

    dynamic = fields.Boolean(
        help="Set this list as dynamic, to make it autosynchronized with "
             "partners from a given criteria.",
    )
    sync_method = fields.Selection(
        [
            ("add", "Only add new records"),
            ("full", "Add and remove records as needed"),
        ],
        default="add",
        required=True,
        help="Choose the syncronization method for this list if you want to "
             "make it dynamic",
    )
    sync_domain = fields.Char(
        string="Synchronization critera",
        default="[('opt_out', '=', False), ('email', '!=', False)]",
        required=True,
        help="Filter partners to sync in this list",
    )

    def action_sync(self):
        """Sync contacts in dynamic lists."""
        Contact = self.env["mail.mass_mailing.contact"]
        Partner = self.env["res.partner"]
        # Skip non-dynamic lists
        dynamic = self.filtered("dynamic").with_context(syncing=True)
        for one in dynamic:
            sync_domain = safe_eval(one.sync_domain) + [("email", "!=", False)]
            desired_partners = Partner.search(sync_domain)
            # Remove undesired contacts when synchronization is full
            if one.sync_method == "full":
                Contact.search([
                    ("list_id", "=", one.id),
                    ("partner_id", "not in", desired_partners.ids),
                ]).unlink()
            current_contacts = Contact.search([("list_id", "=", one.id)])
            current_partners = current_contacts.mapped("partner_id")
            # Add new contacts
            for partner in desired_partners - current_partners:
                Contact.create({
                    "list_id": one.id,
                    "partner_id": partner.id,
                })
        # Invalidate cached contact count
        self.invalidate_cache(["contact_nbr"], dynamic.ids)
