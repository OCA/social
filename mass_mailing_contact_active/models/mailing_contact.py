# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
from odoo import fields, models


class MailingContact(models.Model):

    _inherit = "mailing.contact"

    active = fields.Boolean(default=True)

    def write(self, values):
        res = super().write(values)
        if "active" in values:
            # Have to search to fetch the inactive records
            subscriptions = self.env["mailing.contact.subscription"].search(
                [("contact_id", "in", self.ids), ("active", "!=", values["active"])]
            )
            if subscriptions:
                subscriptions.write({"active": values["active"]})
        return res
