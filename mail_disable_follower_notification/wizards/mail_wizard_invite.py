# Copyright 2025 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailWizardInvite(models.TransientModel):
    _inherit = "mail.wizard.invite"

    notify = fields.Boolean(default=False)
