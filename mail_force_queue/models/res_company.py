# -*- coding: utf-8 -*-
# Copyright 2018 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    force_mail_queue = fields.Boolean("Force Mail queue")
