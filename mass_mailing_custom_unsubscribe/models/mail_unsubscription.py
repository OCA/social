# -*- coding: utf-8 -*-
# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import _, api, fields, models
from .. import exceptions


class MailUnsubscription(models.Model):
    _name = "mail.unsubscription"
    _inherit = "mail.thread"
    _rec_name = "date"

    date = fields.Datetime(
        default=lambda self: self._default_date(),
        required=True)
    email = fields.Char(
        required=True)
    mass_mailing_id = fields.Many2one(
        "mail.mass_mailing",
        "Mass mailing",
        required=True,
        help="Mass mailing from which he was unsubscribed.")
    unsubscriber_id = fields.Reference(
        lambda self: self._selection_unsubscriber_id(),
        "Unsubscriber",
        required=True,
        help="Who was unsubscribed.")
    reason_id = fields.Many2one(
        "mail.unsubscription.reason",
        "Reason",
        ondelete="restrict",
        required=True,
        help="Why the unsubscription was made.")
    details = fields.Char(
        help="More details on why the unsubscription was made.")
    details_required = fields.Boolean(
        related="reason_id.details_required")

    @api.model
    def _default_date(self):
        return fields.Datetime.now()

    @api.model
    def _selection_unsubscriber_id(self):
        """Models that can be linked to a ``mail.mass_mailing``."""
        return self.env["mail.mass_mailing"]._get_mailing_model()

    @api.multi
    @api.constrains("details", "reason_id")
    def _check_details_needed(self):
        """Ensure details are given if required."""
        for one in self:
            if not one.details and one.details_required:
                raise exceptions.DetailsRequiredError(
                    _("Please provide details on why you are unsubscribing."))


class MailUnsubscriptionReason(models.Model):
    _name = "mail.unsubscription.reason"
    _order = "sequence, name"

    name = fields.Char(
        index=True,
        translate=True,
        required=True)
    details_required = fields.Boolean(
        help="Check to ask for more details when this reason is selected.")
    sequence = fields.Integer(
        index=True,
        help="Position of the reason in the list.")
