# Copyright 2022 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    security_done = fields.Selection(
        selection_add=[("team", "Team"), ("all",)], ondelete={"team": "set default"}
    )
    security_edit = fields.Selection(
        selection_add=[("team", "Team"), ("all",)], ondelete={"team": "set default"}
    )
    security_cancel = fields.Selection(
        selection_add=[("team", "Team"), ("all",)], ondelete={"team": "set default"}
    )
