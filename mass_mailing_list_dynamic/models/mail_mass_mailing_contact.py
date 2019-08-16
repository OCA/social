# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2019 Tecnativa - Victor M.M. Torres
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class MassMailingContact(models.Model):
    _inherit = "mail.mass_mailing.contact"

    @api.constrains("partner_id", "list_ids", "name", "email")
    def _check_no_manual_edits_on_fully_synced_lists(self):
        if self.env.context.get("syncing"):
            return
        if any(self.mapped('list_ids').filtered(
                lambda x: x.dynamic and x.sync_method == "full")):
            raise ValidationError(
                _("Cannot edit manually contacts in a fully "
                    "synchronized list. Change its sync method or execute "
                    "a manual sync instead."))
