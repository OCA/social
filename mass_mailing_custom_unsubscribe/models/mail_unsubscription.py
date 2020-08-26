# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

from odoo.addons.mass_mailing.models.mailing import MASS_MAILING_BUSINESS_MODELS

from .. import exceptions


class MailUnsubscription(models.Model):
    _name = "mail.unsubscription"
    _description = "Mail unsubscription"
    _inherit = "mail.thread"
    _rec_name = "date"
    _order = "date DESC"

    date = fields.Datetime(default=lambda self: self._default_date(), required=True)
    email = fields.Char(required=True)
    action = fields.Selection(
        selection=[
            ("subscription", "Subscription"),
            ("unsubscription", "Unsubscription"),
            ("blacklist_add", "Blacklisting"),
            ("blacklist_rm", "De-blacklisting"),
        ],
        required=True,
        default="unsubscription",
        help="What did the (un)subscriber choose to do.",
    )
    mass_mailing_id = fields.Many2one(
        "mailing.mailing",
        "Mass mailing",
        required=True,
        help="Mass mailing from which he was unsubscribed.",
    )
    unsubscriber_id = fields.Reference(
        lambda self: self._selection_unsubscriber_id(),
        "(Un)subscriber",
        help="Who was subscribed or unsubscribed.",
    )
    mailing_list_ids = fields.Many2many(
        comodel_name="mailing.list",
        string="Mailing lists",
        help="(Un)subscribed mass mailing lists, if any.",
    )
    reason_id = fields.Many2one(
        "mail.unsubscription.reason",
        "Reason",
        ondelete="restrict",
        help="Why the unsubscription was made.",
    )
    details = fields.Text(help="More details on why the unsubscription was made.")
    details_required = fields.Boolean(related="reason_id.details_required")
    metadata = fields.Text(
        readonly=True, help="HTTP request metadata used when creating this record."
    )

    def map_mailing_list_models(self, models):
        model_mapped = []
        for model in models:
            if model == "mailing.list":
                model_mapped.append(("mailing.contact", model))
            else:
                model_mapped.append((model, model))
        return model_mapped

    @api.model
    def _default_date(self):
        return fields.Datetime.now()

    @api.model
    def _selection_unsubscriber_id(self):
        """Models that can be linked to a ``mailing.mailing``."""
        model = (
            self.env["ir.model"]
            .search([("model", "in", MASS_MAILING_BUSINESS_MODELS)])
            .mapped("model")
        )
        return self.map_mailing_list_models(model)

    @api.constrains("action", "reason_id")
    def _check_reason_needed(self):
        """Ensure reason is given for unsubscriptions."""
        for one in self:
            unsubscription_states = {"unsubscription", "blacklist_add"}
            if one.action in unsubscription_states and not one.reason_id:
                raise exceptions.ReasonRequiredError(
                    _("Please indicate why are you unsubscribing.")
                )

    @api.constrains("details", "reason_id")
    def _check_details_needed(self):
        """Ensure details are given if required."""
        for one in self:
            if not one.details and one.details_required:
                raise exceptions.DetailsRequiredError(
                    _("Please provide details on why you are unsubscribing.")
                )

    @api.model
    def create(self, vals):
        # No reasons for subscriptions
        if vals.get("action") in {"subscription", "blacklist_rm"}:
            vals = dict(vals, reason_id=False, details=False)
        return super().create(vals)


class MailUnsubscriptionReason(models.Model):
    _name = "mail.unsubscription.reason"
    _description = "Mail unsubscription reason"
    _order = "sequence, name"

    name = fields.Char(index=True, translate=True, required=True)
    details_required = fields.Boolean(
        help="Check to ask for more details when this reason is selected."
    )
    sequence = fields.Integer(index=True, help="Position of the reason in the list.")
