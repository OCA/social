# Copyright 2020 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models, tools


class MailAlias(models.Model):
    _inherit = "mail.alias"

    @api.model
    @tools.ormcache()
    def get_aliases(self):
        """We want to discard these addresses for trackings"""
        aliases = {
            x["display_name"]
            for x in self.search_read([("alias_name", "!=", False)], ["display_name"])
        }
        mail_alias_domain = self.env["mail.alias.domain"].search([])
        catchall_emails = set(mail_alias_domain.mapped("catchall_email"))
        default_from_emails = set(
            mail_alias_domain.filtered("default_from").mapped("default_from_email")
        )
        return aliases | catchall_emails | default_from_emails

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env.registry.clear_cache()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "alias_name" in vals:
            self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res
