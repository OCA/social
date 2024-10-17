# Copyright 2020 Tecnativa - Alexandre Díaz
# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class MailAliasDomain(models.Model):
    _inherit = "mail.alias.domain"

    @api.model_create_multi
    def create(self, vals_list):
        """We've got `mail.alias.get_aliases` method which is cached os we need
        to refresh the cache when we add a new alias domain"""
        res = super().create(vals_list)
        self.env.registry.clear_cache()
        return res

    def write(self, vals):
        """We've got `mail.alias.get_aliases` method which is cached os we need
        to refresh the cache when we add a new alias domain"""
        res = super().write(vals)
        if "catchall_alias" in vals:
            self.env.registry.clear_cache()
        return res

    def unlink(self):
        """We've got `mail.alias.get_aliases` method which is cached os we need
        to refresh the cache when we remove an alias domain"""
        res = super().unlink()
        self.env.registry.clear_cache()
        return res
