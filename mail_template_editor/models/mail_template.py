# Copyright 2025 Kencove - Mohamed Alkobrosli
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class MailTemplate(models.Model):
    _inherit = "mail.template"

    mailing_id = fields.One2many("mailing.mailing", "template_id")

    mailing_count = fields.Integer(
        compute="_compute_mailing_count",
    )

    @api.depends("mailing_id")
    def _compute_mailing_count(self):
        self.ensure_one()
        records = self.env["mailing.mailing"].search(
            [("active", "=", True), ("template_id", "=", self.id)]
        )
        self.mailing_count = len(records)

    def create_mailing_mailing(self):
        self.env["mailing.mailing"].create(
            {
                "subject": self.subject,
                "template_id": self.id,
                "mailing_model_id": self.env.ref("mass_mailing.model_res_partner").id,
            }
        )
        return self.action_view_mailings()

    def apply_mailing_html(self):
        self.ensure_one()
        if len(self.mailing_id) == 1:
            self.body_html = self.mailing_id.body_html

    def action_view_mailings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Mass Mailings"),
            "res_model": "mailing.mailing",
            "view_mode": "tree,form",
            "domain": [("template_id", "=", self.id)],
            "context": {"default_template_id": self.id},
        }
