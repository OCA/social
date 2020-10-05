# Copyright 2020 ADHOC SA
# Nicolás Messina <nm@adhoc.com.ar>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        # TODO evaluar si existe el mismo modelo en más de una etiqueta
        model_tags = self.env["res.partner.category"].search(
            [("auto_subscribe", "=", True), ("model_ids.model", "=", self._name)]
        )
        if model_tags:
            subscribers = (
                self.env["res.partner"]
                .search(
                    [
                        ("parent_id", "=", self.partner_id.id),
                        ("category_id", "in", model_tags.ids),
                    ]
                )
                .ids
            )
            partner_ids.extend(subscribers)
        return super(MailThread, self).message_subscribe(partner_ids)
