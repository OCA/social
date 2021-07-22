# Copyright 2019 O4SB - Graeme Gellatly
# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Onestein - Andrea Stirpe
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class MailMail(models.AbstractModel):
    _inherit = "mail.mail"

    # in messages from objects is adding using Odoo that we are going to remove

    @api.model_create_multi
    def create(self, values_list):
        for index, _value in enumerate(values_list):
            values_list[index]["body_html"] = self.env[
                "mail.render.mixin"
            ].remove_href_odoo(
                values_list[index].get("body_html", ""),
                remove_parent=0,
                remove_before=1,
            )

        return super().create(values_list)
