# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2019 Tecnativa - Victor M.M. Torres
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class MassMailingContact(models.Model):
    _inherit = "mail.mass_mailing.contact"

    def _check_dynamic_full_sync_list(self, mailing_list):
        if mailing_list.dynamic and mailing_list.sync_method == "full":
            raise ValidationError(_(
                "Cannot edit manually contacts in a fully "
                "synchronized list. Change its sync method or execute "
                "a manual sync instead."
            ))

    def _check_no_modification_on_fully_synced_lists(self, vals):
        """Check that no modification is done on fully synced dynamic list.
        We examine then each possible command applied in the m2m field.
        """
        if self.env.context.get("syncing"):
            return
        for command in vals["list_ids"]:
            if command[0] in (1, 2, 3, 4):
                lst = self.env["mail.mass_mailing.list"].browse(command[1])
                self._check_dynamic_full_sync_list(lst)
            elif command[0] in (5, 6):
                for lst in self.mapped("list_ids"):
                    self._check_dynamic_full_sync_list(lst)
                if command[0] == 6:
                    for _id in command[2]:
                        lst = self.env["mail.mass_mailing.list"].browse(_id)
                        self._check_dynamic_full_sync_list(lst)

    @api.constrains("partner_id", "name", "email")
    def _check_no_manual_edits_on_fully_synced_lists(self):
        """We have to avoid also changes in linked partner, name or email."""
        if self.env.context.get("syncing"):
            return
        for lst in self.mapped('list_ids'):
            self._check_dynamic_full_sync_list(lst)

    def write(self, vals):
        if "list_ids" in vals:
            self._check_no_modification_on_fully_synced_lists(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "list_ids" in vals:
                self._check_no_modification_on_fully_synced_lists(vals)
        return super().create(vals_list)
