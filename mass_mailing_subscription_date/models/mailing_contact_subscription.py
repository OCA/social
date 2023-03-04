# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailingContactSubscription(models.Model):
    _inherit = "mailing.contact.subscription"

    subscription_date = fields.Datetime(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if "opt_out" in vals and "subscription_date" not in vals:
                vals["subscription_date"] = now if not vals["opt_out"] else False
            if vals.get("subscription_date"):
                vals["opt_out"] = False
        return super().create(vals_list)

    def write(self, vals):
        if "opt_out" in vals and "subscription_date" not in vals:
            vals["subscription_date"] = (
                fields.Datetime.now() if not vals["opt_out"] else False
            )
        if vals.get("subscription_date"):
            vals["opt_out"] = False
        return super(MailingContactSubscription, self).write(vals)
