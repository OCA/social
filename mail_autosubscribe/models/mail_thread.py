# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # Overload to automatically subscribe autosubscribe followers.
        autosubscribe_followers = not self.env.context.get("no_autosubscribe_followers")
        if partner_ids and autosubscribe_followers:
            partners = self.env["res.partner"].sudo().browse(partner_ids)
            followers = self._message_get_autosubscribe_followers(partners)
            follower_ids = [
                follower.id
                for follower in followers
                if follower not in partners and follower not in self.message_partner_ids
            ]
            partner_ids += follower_ids
        return super().message_subscribe(
            partner_ids=partner_ids,
            subtype_ids=subtype_ids,
        )
