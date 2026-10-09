# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    is_sidebar_hidden = fields.Boolean(
        string="Hidden in Discuss sidebar",
        default=False,
        help=(
            "If enabled, this channel is hidden from the Discuss sidebar "
            "for this member."
        ),
    )

    def _discuss_channel_member_format(self, fields=None):
        include_sidebar_hidden = not fields or fields.get("is_sidebar_hidden")
        member_data = super()._discuss_channel_member_format(fields=fields)
        if include_sidebar_hidden:
            for member, values in member_data.items():
                values["is_sidebar_hidden"] = member.is_sidebar_hidden
        return member_data
