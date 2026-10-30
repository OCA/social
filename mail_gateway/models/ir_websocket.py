# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models
from odoo.http import request

from odoo.addons.bus.websocket import wsrequest


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _build_bus_channel_list(self, channels):
        req = request or wsrequest
        result = super()._build_bus_channel_list(channels)
        if req.session.uid:
            if req.env.user.has_group("mail_gateway.gateway_user"):
                # Only notify gateway channels that the user is still a member of
                # otherwise, bus notifications keep arriving after leaving the channel.
                for channel in req.env["discuss.channel"].search(
                    [("channel_type", "=", "gateway"), ("is_member", "=", True)]
                ):
                    result.append(channel)
        return result
