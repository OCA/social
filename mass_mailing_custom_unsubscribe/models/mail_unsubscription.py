# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class MailUnsubscription(models.Model):
    _name = "mail.unsubscription"
    _description = "Mail unsubscription"
    _inherit = "mail.thread"
    _mail_post_access = "read"
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
        "mailing.subscription.optout",
        "Reason",
        ondelete="restrict",
        help="Why the unsubscription was made.",
    )
    details = fields.Text(help="More details on why the unsubscription was made.")
    is_feedback = fields.Boolean(related="reason_id.is_feedback")
    metadata = fields.Text(help="HTTP request metadata used when creating this record.")

    @api.model
    def _default_date(self):
        return fields.Datetime.now()

    @api.model
    def _selection_unsubscriber_id(self):
        """Models that can be linked to a ``mailing.mailing``."""
        models = self.env["ir.model"].search(
            [("is_mailing_enabled", "=", True), ("model", "!=", "mailing.list")]
        )
        return [(model.model, model.name) for model in models]

    @api.model
    def _fetch_last_unsubcription(self, mailing, res_id, action=None):
        domain = [
            ("mass_mailing_id", "=", mailing.id),
            ("unsubscriber_id", "=", f"{mailing.mailing_model_real},{res_id}"),
        ]
        if action:
            domain += [("action", "=", action)]
        return self.search(domain, limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # No reasons for subscriptions
            if vals.get("action") in {"subscription", "blacklist_rm"}:
                vals = dict(vals, reason_id=False, details=False)
        return super().create(vals_list)
