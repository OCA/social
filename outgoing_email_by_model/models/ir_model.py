# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import fields, models

OUTGOING_MAILSERVER_DESCRIPTION = """
    Allows to force the usage of a given outgoing mail server if this setting is set.
    However, this setting will be active only if the model extends `mail.thread`.
"""
OUTGOING_EMAIL_DESCRIPTION = """
    Allows to force the usage of a given email address if this setting is set.
    However, this setting will be active only if the model extends `mail.thread`.
"""


class IrModel(models.Model):
    _inherit = "ir.model"

    outgoing_mailserver_id = fields.Many2one(
        "ir.mail_server", help=OUTGOING_MAILSERVER_DESCRIPTION
    )
    outgoing_email = fields.Char(help=OUTGOING_EMAIL_DESCRIPTION)
