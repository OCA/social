# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class BaseModel(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _message_get_autosubscribe_followers_domain(self, partners):
        return [
            ("id", "child_of", partners.commercial_partner_id.ids),
            ("mail_autosubscribe_ids.model", "=", self._name),
        ]

    @api.model
    def _message_get_autosubscribe_followers(self, partners):
        domain = self._message_get_autosubscribe_followers_domain(partners)
        return self.env["res.partner"].sudo().search(domain)

    def _message_get_default_recipients(self):
        # Overload to include auto follow document partners in the composer
        # Note: This only works if the template is configured with 'Default recipients'
        res = super()._message_get_default_recipients()
        if self.env.context.get("no_autosubscribe_followers"):
            return res
        for rec in self:
            partner_ids = res[rec.id]["partner_ids"]
            partners = self.env["res.partner"].sudo().browse(partner_ids)
            followers = rec._message_get_autosubscribe_followers(partners)
            follower_ids = [
                follower.id for follower in followers if follower not in partners
            ]
            partner_ids += follower_ids
        return res
