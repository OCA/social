from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_excluded_partners_domain(self):
        return [
            ("active", "in", (True, False)),
            ("show_in_cc", "=", False),
            ("groups_id", "not in", self.env.ref("base.group_portal").ids),
        ]

    @api.model
    def _get_excluded_partners(self):
        domain = self._get_excluded_partners_domain()
        return self.env["res.users"].search(domain).mapped("partner_id")

    def _show_in_cc(self, show_internal_users):
        self.ensure_one()
        if not self.user_ids:
            return True
        excluded_partners = self._get_excluded_partners()
        if show_internal_users:
            return self not in excluded_partners and self.user_ids.mapped("show_in_cc")
        else:
            return self not in excluded_partners and self.env.ref(
                "base.group_portal"
            ) not in self.user_ids.mapped("groups_id")
