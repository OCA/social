# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import models

from .assetsbundle import AssetsMailChatterThreadColourBundle


class QWeb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _get_asset_content(self, xmlid, options):
        """Handle 'special' chatter_thread_colour_assets xmlid"""
        if xmlid == "mail_chatter_thread_colour.chatter_thread_colour_assets":
            asset = AssetsMailChatterThreadColourBundle(xmlid, [], env=self.env)
            return ([], [asset.get_mail_chatter_thread_colour_asset_node()])
        return super()._get_asset_content(xmlid, options)
