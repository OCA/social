# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post_with_template(
        self, template_id, email_layout_xmlid=None, **kwargs
    ):
        # OVERRIDE to force the email_layout_xmlid defined on the mail.template
        template = self.env["mail.template"].sudo().browse(template_id)
        if template.force_email_layout_id:
            email_layout_xmlid = template.force_email_layout_id.xml_id
        return super().message_post_with_template(
            template_id, email_layout_xmlid=email_layout_xmlid, **kwargs
        )
