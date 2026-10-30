# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.mail.wizard.mail_template_preview import MailTemplatePreview


class MailTemplatePreview(models.TransientModel):
    _inherit = "mail.template.preview"

    _MAIL_TEMPLATE_FIELDS = MailTemplatePreview._MAIL_TEMPLATE_FIELDS + ["email_bcc"]

    email_bcc = fields.Char(
        "Bcc",
        compute="_compute_mail_template_fields",
        help="Blind Carbon copy recipients",
    )
