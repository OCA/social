# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    default_team_id = fields.Many2one(comodel_name="mail.activity.team")
