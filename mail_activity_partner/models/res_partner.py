# Copyright 2023 Akretion (https://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    activity_count = fields.Integer(compute="_compute_activity_count")

    def _get_activity_domain(self):
        self.ensure_one()
        return [("partner_id", "child_of", self.id)]

    def _compute_activity_count(self):
        for record in self:
            domain = record._get_activity_domain()
            record.activity_count = self.env["mail.activity"].search_count(domain)

    def action_view_activity(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mail.mail_activity_action")
        action["domain"] = self._get_activity_domain()
        return action
