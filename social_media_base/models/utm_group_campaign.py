# Copyright 2025 Kencove (https://www.kencove.com/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class UtmGroupCampaign(models.Model):
    _name = "utm.group.campaign"
    _description = "UTM Group Campaign"

    name = fields.Char()
