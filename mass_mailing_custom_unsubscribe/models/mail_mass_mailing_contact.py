# Copyright 2018 David Vidal <david.vidal@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailMassMailing(models.Model):
    _inherit = "mail.mass_mailing.contact"

    # Recover the old Many2one field so we can set a contact by list
    mailing_list_id = fields.Many2one(
        'mail.mass_mailing.list',
        string='Mailing List',
        ondelete='cascade',
        compute="_compute_mailing_list_id",
        inverse="_inverse_mailing_list_id",
        search="_search_mailing_list_id",
    )

    @api.depends('list_ids')
    def _compute_mailing_list_id(self):
        for contact in self:
            contact.mailing_list_id = contact.list_ids[:1]

    def _inverse_mailing_list_id(self):
        for contact in self:
            contact.list_ids = contact.mailing_list_id

    def _search_mailing_list_id(self, operator, value):
        return [('list_ids', operator, value)]
