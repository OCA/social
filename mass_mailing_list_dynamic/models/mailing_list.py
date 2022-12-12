# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2020 Hibou Corp. - Jared Kipe
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class MassMailingList(models.Model):
    _inherit = "mailing.list"

    dynamic = fields.Boolean(
        help="Set this list as dynamic, to make it autosynchronized with "
        "partners from a given criteria."
    )
    sync_method = fields.Selection(
        selection=[
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
        help="Helper field to make the user aware of unsynced changes", default=True
    )

    def action_sync(self):
        """Sync contacts in dynamic lists."""
        Contact = self.env["mailing.contact"].with_context(syncing=True)
        Partner = self.env["res.partner"]
        # Skip non-dynamic lists
        dynamic = self.filtered("dynamic").with_context(syncing=True)
        for one in dynamic:
            sync_domain = [("email", "!=", False)] + safe_eval(one.sync_domain)
            desired_partners = Partner.search(sync_domain)
            # Detach or remove undesired contacts when synchronization is full
            if one.sync_method == "full":
                contact_to_detach = one.contact_ids.filtered(
                    lambda r: r.partner_id not in desired_partners
                )
                one.contact_ids -= contact_to_detach
                contact_to_detach.filtered(lambda r: not r.list_ids).unlink()
            # Add new contacts
            current_partners = one.contact_ids.mapped("partner_id")
            contact_to_list = self.env["mailing.contact"]
            vals_list = []
            for partner in desired_partners - current_partners:
                contacts_in_partner = partner.mass_mailing_contact_ids
                if contacts_in_partner:
                    contact_to_list |= contacts_in_partner[0]
                else:
                    vals_list.append(
                        {"list_ids": [(4, one.id)], "partner_id": partner.id}
                    )
            one.contact_ids |= contact_to_list
            Contact.create(vals_list)
            one.is_synced = True
        # Invalidate cached contact count
        self.invalidate_cache(["contact_nbr"], dynamic.ids)

    @api.onchange("dynamic", "sync_method", "sync_domain")
    def _onchange_dynamic(self):
        if self.dynamic:
            self.is_synced = False
