# Copyright 2016 Tecnativa - Antonio Espinosa
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import copy

from odoo import fields, models


def event_filtered_ids(model, mailing_mailing_id, domain, field="email"):
    field = field or "email"
    domain = domain or []
    exclude_emails = []
    mailing_mailing = model.env["mailing.mailing"].browse(mailing_mailing_id)
    if mailing_mailing.event_id:
        exclude = mailing_mailing.exclude_event_state_ids.mapped("code")
        reg_domain = False
        registrations = model.env["event.registration"]
        if exclude:
            reg_domain = [
                ("event_id", "=", mailing_mailing.event_id.id),
                ("state", "in", exclude),
            ]
        if reg_domain:
            registrations = registrations.search(reg_domain)
        if registrations:
            exclude_emails = registrations.mapped("email")
    apply_domain = copy.deepcopy(domain)
    if exclude_emails:
        apply_domain.append((field, "not in", exclude_emails))
    rows = model.search(apply_domain)
    return rows.ids


class MassMailing(models.Model):
    _inherit = "mailing.mailing"

    def _default_exclude_event_state_ids(self):
        return self.env["event.registration.state"].search([])

    event_id = fields.Many2one(string="Event related", comodel_name="event.event")
    exclude_event_state_ids = fields.Many2many(
        comodel_name="event.registration.state",
        string="Exclude",
        default=_default_exclude_event_state_ids,
    )

    def _get_recipients(self):
        res_ids = super()._get_recipients()
        if res_ids:
            domain = [("id", "in", res_ids)]
            res_ids = event_filtered_ids(
                self.env[self.mailing_model_real], self.id, domain, field="email"
            )
        return res_ids
