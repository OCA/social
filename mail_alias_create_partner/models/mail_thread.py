# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model
    def _message_route_process(self, message, message_dict, routes):
        # create a partner if there is a route with an alias that is configured to do so
        for _model, _thread_id, _custom_values, _user_id, alias in routes or ():
            if (
                alias
                and alias.alias_create_partner
                and not message_dict.get("author_id")
            ):
                message_dict["author_id"] = alias._alias_create_partner(message_dict).id

        return super()._message_route_process(message, message_dict, routes)
