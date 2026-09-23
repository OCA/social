# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _get_self_member(self):
        self.ensure_one()
        current_partner, current_guest = self.env["res.partner"]._get_current_persona()
        domain = [("channel_id", "=", self.id)]
        if current_partner:
            domain.append(("partner_id", "=", current_partner.id))
        elif current_guest:
            domain.append(("guest_id", "=", current_guest.id))
        else:
            return self.env["discuss.channel.member"]
        return self.env["discuss.channel.member"].search(domain, limit=1)

    def action_set_sidebar_hidden(self, hidden=True):
        self.ensure_one()
        member = self._get_self_member()
        if not member:
            return
        vals = {"is_sidebar_hidden": bool(hidden)}
        if hidden:
            vals["is_pinned"] = False
        member.write(vals)
        if hidden:
            # Keep native unpin bus behavior for immediate UI feedback.
            self.env["bus.bus"]._sendone(
                self.env.user.partner_id, "discuss.channel/unpin", {"id": self.id}
            )
        else:
            self.env["bus.bus"]._sendone(
                self.env.user.partner_id,
                "mail.record/insert",
                {"Thread": self._channel_info()[0]},
            )

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, *, message_type="notification", **kwargs):
        # Any new activity makes hidden channels visible again for members.
        self.sudo().channel_member_ids.write({"is_sidebar_hidden": False})
        return super().message_post(message_type=message_type, **kwargs)
