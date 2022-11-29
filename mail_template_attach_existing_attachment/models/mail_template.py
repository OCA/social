# Copyright 2022 Foodles (http://www.foodles.co).
# @author Pierre Verkest <pierreverkest84@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailTemplate(models.Model):
    "Templates for sending email"
    _inherit = "mail.template"

    attach_exist_document_regex = fields.Char(
        string="Attachment name pattern (regex)",
        help=(
            "REGular EXpression to find existing document (base on file name) "
            "to attach in mass mailing or by default in mail composer"
        ),
    )

    @api.constrains("attach_exist_document_regex")
    def validate_regex(self):
        for record in self:
            try:
                if record.attach_exist_document_regex:
                    re.compile(record.attach_exist_document_regex)
            except re.error:
                raise ValidationError(
                    _(
                        "The following regular expression is invalid to select attachment: %s"
                    )
                    % record.attach_exist_document_regex
                )
