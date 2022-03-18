# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    mail_autosubscribe_ids = fields.Many2many(
        "mail.autosubscribe",
        string="Autosubscribe Models",
        column1="partner_id",
        column2="model_id",
    )

    def _has_autosubscription_to(self, model_name: str) -> bool:
        """Checks whether partner has auto-subscription to a specific model

        :param str model_name: model technical name
        :returns: True if partner has auto-subscription on given model
        """
        self.ensure_one()
        return bool(
            self.mail_autosubscribe_ids
            and model_name in self.mail_autosubscribe_ids.mapped("model")
        )
