# Copyright 2021 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from lxml import html as lxml_html

from odoo import api, fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    uses_forms = fields.Boolean(compute="_compute_uses_forms")

    @api.depends("default_description")
    def _compute_uses_forms(self):
        attribute_xpath = "//*[%s]" % (
            " or ".join(
                "@%s" % attribute
                for attribute in self.env[
                    "mail.activity"
                ]._mail_activity_form_attributes()
            )
        )
        for this in self:
            if not this.default_description:
                this.uses_forms = False
                continue
            this.uses_forms = bool(
                lxml_html.fromstring(this.default_description).xpath(attribute_xpath)
            )
