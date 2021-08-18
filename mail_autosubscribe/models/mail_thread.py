# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
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
            partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids,
        )

    @api.model
    def _message_get_default_recipients_on_records(self, records):
        # Overload to include auto follow document partners in the composer
        # Note: This only works if the template is configured with 'Default recipients'
        res = super()._message_get_default_recipients_on_records(records)
        if records.env.context.get("no_autosubscribe_followers"):
            return res
        for rec in records:
            partner_ids = res[rec.id]["partner_ids"]
            partners = self.env["res.partner"].sudo().browse(partner_ids)
            followers = rec._message_get_autosubscribe_followers(partners)
            follower_ids = [
                follower.id for follower in followers if follower not in partners
            ]
            partner_ids += follower_ids
        return res
