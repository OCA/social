# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2019 Tecnativa - Victor M.M. Torres
# Copyright 2020 Hibou Corp. - Jared Kipe
# Copyright 2025 CorporateHub (https://corporatehub.eu) - Alexey Pelykh
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import ValidationError


class MassMailingContact(models.Model):
    _inherit = "mailing.contact"

    def create(self, vals_list):
        if self.env.context.get("syncing") or self.env.context.get(
            "from_message_receive_bounce"
        ):
            return super().create(vals_list)

        mailing_contacts = super().create(vals_list)

        full_synced_lists = mailing_contacts.mapped("list_ids").filtered(
            lambda x: x.dynamic and x.sync_method == "full"
        )
        if full_synced_lists:
            raise ValidationError(
                _(
                    "Cannot add contacts to a fully "
                    "synchronized list. Change its sync method or execute "
                    "a manual sync instead."
                )
            )

        return mailing_contacts

    def write(self, vals):
        if self.env.context.get("syncing") or self.env.context.get(
            "from_message_receive_bounce"
        ):
            return super().write(vals)

        if ("partner_id" in vals or "name" in vals or "email" in vals) and self.mapped(
            "list_ids"
        ).filtered(lambda x: x.dynamic and x.sync_method == "full"):
            raise ValidationError(
                _(
                    "Cannot edit manually contacts in a fully "
                    "synchronized list. Change its sync method or execute "
                    "a manual sync instead."
                )
            )

        if "list_ids" not in vals:
            return super().write(vals)

        old_list_ids_by_mailing_contact = {
            mailing_contact.id: mailing_contact.list_ids for mailing_contact in self
        }

        res = super().write(vals)

        new_list_ids_by_mailing_contact = {
            mailing_contact.id: mailing_contact.list_ids for mailing_contact in self
        }

        for mailing_contact in self:
            old_list_ids = old_list_ids_by_mailing_contact[mailing_contact.id]
            new_list_ids = new_list_ids_by_mailing_contact[mailing_contact.id]
            if new_list_ids == old_list_ids:
                continue

            removed_full_synced_lists = (old_list_ids - new_list_ids).filtered(
                lambda x: x.dynamic and x.sync_method == "full"
            )
            if removed_full_synced_lists:
                raise ValidationError(
                    _(
                        "Cannot remove contacts from a fully "
                        "synchronized list. Change its sync method or execute "
                        "a manual sync instead."
                    )
                )

            added_full_synced_lists = (new_list_ids - old_list_ids).filtered(
                lambda x: x.dynamic and x.sync_method == "full"
            )
            if added_full_synced_lists:
                raise ValidationError(
                    _(
                        "Cannot add contacts to a fully "
                        "synchronized list. Change its sync method or execute "
                        "a manual sync instead."
                    )
                )

        return res
