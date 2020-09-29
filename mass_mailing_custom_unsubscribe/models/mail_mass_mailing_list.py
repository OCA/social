# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMassMailing(models.Model):
    _inherit = "mailing.list"

    not_cross_unsubscriptable = fields.Boolean(
        string="Not cross unsubscriptable",
        help="If you mark this field, this list won't be shown when "
        "unsubscribing from other mailing list, in the section: "
        "'Is there any other mailing list you want to leave?'",
    )
