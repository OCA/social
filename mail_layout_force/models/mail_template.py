# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    force_email_layout_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Force Layout",
        domain=[("type", "=", "qweb"), ("mode", "=", "primary")],
        compute="_compute_force_email_layout_id",
        inverse="_inverse_force_email_layout_id",
        help="Force a mail layout for this template.",
    )

    @api.depends("email_layout_xmlid")
    def _compute_force_email_layout_id(self):
        for template in self:
            if template.email_layout_xmlid:
                template.force_email_layout_id = self.env.ref(
                    template.email_layout_xmlid, raise_if_not_found=False
                )
            else:
                template.force_email_layout_id = False

    def _inverse_force_email_layout_id(self):
        for template in self:
            if template.force_email_layout_id:
                template.email_layout_xmlid = template.force_email_layout_id.xml_id
            else:
                template.email_layout_xmlid = False
