# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailingContactSubscription(models.Model):
    _inherit = "mailing.contact.subscription"

    subscription_date = fields.Datetime(readonly=True)

    @api.model
    def create(self, vals):
        vals["subscription_date"] = not vals.get("opt_out") and fields.Datetime.now()
        return super().create(vals)

    def write(self, vals):
        if "opt_out" in vals:
            vals["subscription_date"] = not vals["opt_out"] and fields.Datetime.now()
        return super().write(vals)
