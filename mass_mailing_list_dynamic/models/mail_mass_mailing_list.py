# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
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
        default="[('is_blacklisted', '=', False), ('email', '!=', False)]",
        required=True,
        help="Filter partners to sync in this list",
    )
    is_synced = fields.Boolean(
        help="Helper field to make the user aware of unsynced changes",
        default=True,
    )

    def action_sync(self):
        """Sync contacts in dynamic lists."""
        Contact = self.env["mail.mass_mailing.contact"].with_context(
            syncing=True,
        )
        Partner = self.env["res.partner"]
        # Skip non-dynamic lists
        dynamic = self.filtered("dynamic")
        for one in dynamic:
            sync_domain = safe_eval(one.sync_domain) + [("email", "!=", False)]
            desired_partners = Partner.search(sync_domain)
            # Remove undesired contacts when synchronization is full
            if one.sync_method == "full":
                Contact.search([
                    ("list_ids", "in", one.id),
                    ("partner_id", "not in", desired_partners.ids),
                ]).unlink()
            current_contacts = Contact.search([("list_ids", "in", one.id)])
            current_partners = current_contacts.mapped("partner_id")
            # Add new contacts
            vals_list = []
            for partner in desired_partners - current_partners:
                vals_list.append({
                    "list_ids": [(4, one.id)],
                    "partner_id": partner.id,
                })
            Contact.create(vals_list)
            one.is_synced = True
        # Invalidate cached contact count
        self.invalidate_cache(["contact_nbr"], dynamic.ids)

    @api.onchange("dynamic", "sync_method", "sync_domain")
    def _onchange_dynamic(self):
        if self.dynamic:
            self.is_synced = False
