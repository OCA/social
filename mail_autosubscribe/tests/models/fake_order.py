# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FakeOrder(models.Model):
    _name = "fake.order"
    _inherit = "mail.thread"
    _description = "Fake sale.order like model"

    partner_id = fields.Many2one("res.partner", required=True)
