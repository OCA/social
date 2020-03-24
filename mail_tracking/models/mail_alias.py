# Copyright 2020 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, tools


class MailAlias(models.Model):
    _inherit = 'mail.alias'

    @api.model
    @tools.ormcache()
    def get_aliases(self):
        return set(x['display_name'] for x in self.search_read([
            ('alias_name', '!=', False),
        ], ['display_name']))

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.clear_caches()
        return res

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if 'alias_name' in vals:
            self.clear_caches()
        return res

    @api.multi
    def unlink(self):
        res = super().unlink()
        self.clear_caches()
        return res
