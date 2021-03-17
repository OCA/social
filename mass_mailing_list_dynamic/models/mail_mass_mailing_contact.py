# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2019 Tecnativa - Victor M.M. Torres
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class MassMailingContact(models.Model):
    _inherit = "mail.mass_mailing.contact"

    def _check_dynamic_full_sync_list(self, mailing_list):
        if (
            mailing_list.dynamic and mailing_list.sync_method == "full"
            and not self.env.context.get("bypass_dynamic_list_check")
        ):
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
        List = self.env["mail.mass_mailing.list"]
        for command in vals.get("list_ids", []):
            if command[0] in (1, 2, 3, 4):
                self._check_dynamic_full_sync_list(List.browse(command[1]))
            elif command[0] == 5:
                for lst in self.mapped("list_ids"):
                    self._check_dynamic_full_sync_list(lst)
            elif command[0] == 6:
                for record in self:
                    old_ids = set(record.list_ids.ids)
                    new_ids = set(command[2])
                    to_check_ids = (old_ids - new_ids) | (new_ids - old_ids)
                    for lst in List.browse(to_check_ids):
                        self._check_dynamic_full_sync_list(lst)
        if any(x in vals for x in {"partner_id", "name", "email"}):
            for lst in self.mapped("list_ids"):
                self._check_dynamic_full_sync_list(lst)

    def write(self, vals):
        self._check_no_modification_on_fully_synced_lists(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_no_modification_on_fully_synced_lists(vals)
        return super().create(vals_list)
