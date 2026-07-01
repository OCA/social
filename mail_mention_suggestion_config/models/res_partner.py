# Copyright 2026 Alberto Martínez <alberto.martinez@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_mention_suggestions_domain(self, search):
        """Returns a different suggestion domain based on the config option
        This domains are based on odoo's _search_mention_suggestions()
        additional domains
        """
        res = super()._get_mention_suggestions_domain(search)
        option = self.env.company.mail_mention_suggestion_option
        if option == "users":
            # Suggest partners that are related to any kind of users.
            res = expression.AND(
                [[("user_ids", "!=", False)], [("user_ids.active", "=", True)], res]
            )
        elif option == "users_internal":
            # Suggest partners related to internal users.
            res = expression.AND(
                [
                    [("user_ids", "!=", False)],
                    [("user_ids.active", "=", True)],
                    [("partner_share", "=", False)],
                    res,
                ]
            )
        return res

    def _search_mention_suggestions(self, domain, limit, extra_domain=None):
        # This function overwrites the domain adding more options.
        # As we do not want that, we omit calling super if a custom config option
        # has been selected
        if self.env.company.mail_mention_suggestion_option:
            res = self.search(domain, limit=limit)
        else:
            res = super()._search_mention_suggestions(domain, limit, extra_domain)
        return res

    @api.readonly
    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """Puts the is_suggestion check in the returned data
        to distinguish valid suggestions from cached contacts in OWL"""
        res = super().get_mention_suggestions(search, limit)
        for records_json in res.values():
            for rec_json in records_json:
                rec_json["is_suggestion"] = True
        return res
