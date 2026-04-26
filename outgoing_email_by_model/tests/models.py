# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models


class ModelWithMail(models.Model):
    _name = "model.with.mail"
    _inherit = ["mail.thread"]

    partner_id = fields.Many2one("res.partner")
