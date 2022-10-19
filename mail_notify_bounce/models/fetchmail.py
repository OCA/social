# Copyright 2017 Lorenzo Battistini - Agile Business Group
# Copyright 2022 Simone Vanin - Agile Business Group
# Copyright 2022 Alex Comba - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class FetchmailServer(models.Model):
    _inherit = "fetchmail.server"

    bounce_notify_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="mnb_fetchmail_server_res_partner_rel",
        column1="fetchmail_server_id",
        column2="res_partner_id",
        string="Notify bounce emails to",
    )
