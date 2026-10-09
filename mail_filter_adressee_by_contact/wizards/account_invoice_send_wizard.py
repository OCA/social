# Copyright (C) 2022 Akretion (<http://www.akretion.com>).
# @author Kévin Roche <kevin.roche@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _name = "account.move.send.wizard"
    _inherit = ["account.move.send.wizard", "mail.filter.addressee.mixin"]

    _partner_ids_field = "mail_partner_ids"
