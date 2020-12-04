# Copyright 2020 ADHOC SA
# Nicolás Messina <nm@adhoc.com.ar>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        model_tags = self.env["res.partner.category"].search(
            [("auto_subscribe", "=", True), ("model_ids.model", "=", self._name)]
        )
        if model_tags:
            added_partners = []
            for partner_id in partner_ids:
                subscribers = self.env["res.partner"].search(
                    [
                        (
                            "commercial_partner_id",
                            "=",
                            self.env["res.partner"]
                            .browse(partner_id)
                            .commercial_partner_id.id,
                        ),
                        ("id", "!=", partner_id),
                        ("category_id", "in", model_tags.ids),
                    ]
                )
                added_partners.extend(subscribers.ids)
            partner_ids.extend(added_partners)
        return super().message_subscribe(
            partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids
        )
