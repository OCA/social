# -*- coding: utf-8 -*-
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime
from openerp import api, fields, models
from .. import exceptions


class MailUnsubscription(models.Model):
    _name = "mail.unsubscription"
    _inherit = "mail.thread"
    _rec_name = "date"

    date = fields.Datetime(
        default=lambda self: self._default_date(),
        required=True)
    email = fields.Char(
        required=True,)
    mass_mailing_id = fields.Many2one(
        "mail.mass_mailing",
        "Mass mailing",
        help="Mass mailing from which he was unsubscribed.")
    unsubscriber_id = fields.Reference(
        lambda self: self._selection_unsubscriber_id(),
        "Unsubscriber",
        required=True,
        help="Who he was unsubscribed.")
    reason_id = fields.Many2one(
        "mail.unsubscription.reason",
        "Reason",
        ondelete="restrict",
        required=True,
        help="Why he was unsubscribed.")
    details = fields.Char(
        help="More details on why he was unsubscribed.")
    details_required = fields.Boolean(
        related="reason_id.details_required")
    success = fields.Boolean(
        help="If this is unchecked, it indicates some failure happened in the "
             "unsubscription process.")

    @api.model
    def _default_date(self):
        return datetime.now()

    @api.model
    def _selection_unsubscriber_id(self):
        """Models that can be linked to a ``mail.mass_mailing``."""
        return self.env["mail.mass_mailing"]._get_mailing_model()

    @api.multi
    @api.constrains("details", "reason_id")
    def _check_details_needed(self):
        """Ensure details are given if required."""
        for s in self:
            if not s.details and s.reason_id.details_required:
                raise exceptions.DetailsRequiredError()


class MailUnsubscriptionReason(models.Model):
    _name = "mail.unsubscription.reason"
    _order = "sequence, name"

    name = fields.Char(
        index=True,
        translate=True)
    details_required = fields.Boolean(
        help="Check to ask for more details when this reason is selected.")
    sequence = fields.Integer(
        index=True,
        help="Position of the reason in the list.")
