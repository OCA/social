# Copyright 2020 Alexandre Díaz <dev@redneboa.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.base.models.assetsbundle import AssetsBundle


class AssetsMailChatterThreadColourBundle(AssetsBundle):
    def get_mail_chatter_thread_colour_asset_node(self):
        models = self.env["ir.model"].search([("is_mail_thread", "=", True)])
        result = []
        base_color = (
            self.env["ir.config_parameter"].sudo().get_param("mail_chatter.base_colour")
        )
        base_font_color = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("mail_chatter.base_font_colour")
        )
        for model in models:
            result.append(
                """.o_ChatWindowHeader[data-thread-model="%s"]
                {background-color: %s; color: %s}"""
                % (
                    model.model,
                    model.thread_colour or base_color,
                    model.thread_font_colour or base_font_color,
                )
            )
        return ("style", {}, "".join(result))
