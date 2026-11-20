# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[("validation", "Validation")])
    validator_group_ids = fields.Many2many(
        "res.groups",
        "mail_activity_groups_rel",
        "activity_id",
        "group_id",
    )
