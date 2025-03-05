# Copyright 2024 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailGuestManage(models.TransientModel):
    _name = "mail.guest.manage"
    _description = "Assign gateway guest to a partner"

    guest_id = fields.Many2one("mail.guest", required=True)
    partner_id = fields.Many2one("res.partner")

    def create_partner(self):
        partner = self.env["res.partner"].create(self._get_partner_vals())
        self._merge_partner(partner)
        return partner.get_formview_action()

    def _get_partner_vals(self):
        return {
            "name": self.guest_id.name,
        }

    def _merge_partner(self, partner):
        self.env["res.partner.gateway.channel"].create(
            {
                "name": self.guest_id.gateway_id.name,
                "partner_id": partner.id,
                "gateway_id": self.guest_id.gateway_id.id,
                "gateway_token": self.guest_id.gateway_token,
            }
        )
        for member in self.env["discuss.channel.member"].search(
            [("guest_id", "=", self.guest_id.id)]
        ):
            self.env["discuss.channel.member"].create(
                self._channel_member_vals(member, partner)
            )
            member.unlink()
        self.env["mail.message"].search(
            [("author_guest_id", "=", self.guest_id.id)]
        ).write(
            {
                "author_id": partner.id,
            }
        )

    def _channel_member_vals(self, member, partner):
        return {
            "guest_id": False,
            "channel_id": member.channel_id.id,
            "partner_id": partner.id,
        }

    def merge_partner(self):
        self._merge_partner(self.partner_id)
        return self.partner_id.get_formview_action()
