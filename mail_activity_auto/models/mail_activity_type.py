# Copyright 2016-22 PESOL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    auto = fields.Boolean()
    auto_action_ids = fields.One2many(
        comodel_name="mail.activity.type.action",
        inverse_name="mail_activity_type_id",
        string="Automated Actions",
    )
