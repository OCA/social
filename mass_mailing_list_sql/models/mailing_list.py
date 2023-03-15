# Copyright (C) 2023 ForgeFlow, S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MassMailingList(models.Model):
    _name = "mailing.list"
    _inherit = ["mailing.list", "sql.request.mixin"]

    sql_search = fields.Boolean(
        string="Use SQL Search",
        help="Enable this option to define an SQL query for "
        "selecting partners in the mailing list.",
    )

    def action_sync(self):
        if self.dynamic:
            super().action_sync()
        if self.sql_search and self.query:
            # Synchronize mailing list contacts based on the SQL query
            mailing_lists = self.filtered("sql_search").with_context(syncing=True)
            for mailing_list in mailing_lists:
                mailing_list.button_validate_sql_expression()
                if mailing_lists.state == "sql_valid":
                    sync_query = mailing_lists.query
                    self.env.cr.execute(sync_query)
                    desired_partners = self.env["res.partner"].browse(
                        [r[0] for r in self.env.cr.fetchall()]
                    )
                    if mailing_list.sync_method == "full":
                        contact_to_detach = mailing_list.contact_ids.filtered(
                            lambda r: r.partner_id not in desired_partners
                        )
                        mailing_list.contact_ids -= contact_to_detach
                        contact_to_detach.filtered(lambda r: not r.list_ids).unlink()
                    current_partners = mailing_list.contact_ids.mapped("partner_id")
                    contact_to_list = self.env["mailing.contact"]
                    vals_list = []
                    for partner in desired_partners - current_partners:
                        contacts_in_partner = partner.mass_mailing_contact_ids
                        if contacts_in_partner:
                            contact_to_list |= contacts_in_partner[0]
                        else:
                            vals_list.append(
                                {
                                    "list_ids": [(4, mailing_list.id)],
                                    "partner_id": partner.id,
                                }
                            )
                    mailing_list.contact_ids |= contact_to_list
                    self.env["mailing.contact"].with_context(syncing=True).create(
                        vals_list
                    )
                    mailing_list.is_synced = True
                self.invalidate_cache(["contact_nbr"], mailing_lists.ids)

    @api.onchange("sql_search", "sync_method", "query")
    def _onchange_dynamic(self):
        if self.sql_search:
            self.is_synced = False

    @api.onchange("query")
    def _onchange_query(self):
        if self.sql_search:
            self.button_validate_sql_expression()
