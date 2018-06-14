# Copyright 2017 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class MassMailingContact(models.Model):
    _inherit = "mail.mass_mailing.contact"

    @api.constrains("partner_id", "list_ids", "name", "email")
    def _check_no_manual_edits_on_fully_synced_lists(self):
        if self.env.context.get("syncing"):
            return
        for one in self:
            if any((list.dynamic and
                    list.sync_method == "full") for list in one.list_ids):
        # if any((one.list_id.dynamic and
        #         one.list_id.sync_method == "full") for one in self):
                raise ValidationError(
                    _("Cannot edit manually contacts in a fully "
                        "synchronized list. Change its sync method or execute "
                        "a manual sync instead."))
