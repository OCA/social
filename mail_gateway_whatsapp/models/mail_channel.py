# Copyright 2024 Dixmit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.modules.module import get_resource_path

from odoo.addons.base.models.avatar_mixin import get_hsl_from_seed


class MailChannel(models.Model):

    _inherit = "mail.channel"

    def _generate_avatar_gateway(self):
        if self.gateway_id.gateway_type == "whatsapp":
            path = get_resource_path(
                "mail_gateway_whatsapp", "static/description", "icon.svg"
            )
            with open(path, "r") as f:
                avatar = f.read()

            bgcolor = get_hsl_from_seed(self.uuid)
            avatar = avatar.replace("fill:#875a7b", f"fill:{bgcolor}")
            return avatar
        return super()._generate_avatar_gateway()
