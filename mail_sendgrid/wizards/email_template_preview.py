# Copyright 2015-2017 Compassion CH (http://www.compassion.ch)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class EmailTemplatePreview(models.TransientModel):
    """ Put the preview inside sendgrid template """

    _inherit = "mail.template.preview"

    @api.depends("lang", "resource_ref")
    def _compute_mail_template_fields(self):
        result = super(EmailTemplatePreview, self)._compute_mail_template_fields()
        body_html = self.body_html
        template = self.mail_template_id
        sendgrid_template = template.sendgrid_localized_template
        if sendgrid_template and body_html:
            self.body_html = sendgrid_template.html_content.replace(
                "<%body%>", body_html
            )
        return result
