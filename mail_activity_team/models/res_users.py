# Copyright 2018 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    activity_team_ids = fields.Many2many(
        comodel_name="mail.activity.team",
        relation="mail_activity_team_users_rel",
        string="Activity Teams",
    )
