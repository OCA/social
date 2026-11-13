# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MailMessageImportIncident(models.Model):
    """Something the module could not do or decide safely, for a person to
    review. The processors add their own types of incident."""

    _name = "mail.message.import.incident"
    _description = "Message Import Incident"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "state, id desc"

    name = fields.Char(string="Summary", required=True)
    incident_type = fields.Selection(
        [("processing_error", "Processing error")], string="Type", required=True
    )
    category = fields.Selection(
        [
            ("technical", "Technical error"),
            ("incomplete", "Incomplete data"),
            ("review", "Human assessment"),
        ],
        compute="_compute_category",
        store=True,
    )
    state = fields.Selection(
        [("open", "Open"), ("resolved", "Resolved"), ("dismissed", "Dismissed")],
        default="open",
        required=True,
        tracking=True,
        index=True,
    )
    description = fields.Text()
    company_id = fields.Many2one("res.company", required=True, readonly=True)
    sender_id = fields.Many2one(
        "mail.message.import.sender", string="Sender", readonly=True, index=True
    )
    channel_id = fields.Many2one(
        "mail.message.import.channel", string="Receiving channel", readonly=True
    )
    conversation_id = fields.Many2one(
        "mail.message.import.conversation",
        string="Conversation",
        readonly=True,
        index=True,
    )
    # Where it came from, to divide the incidents by channel and address
    authorized_address_id = fields.Many2one(
        related="conversation_id.authorized_address_id", store=True, string="Sent from"
    )
    origin_display = fields.Char(related="conversation_id.origin_display")
    message_id = fields.Many2one("mail.message.import.message", readonly=True)
    resolution_note = fields.Text()
    resolved_by_id = fields.Many2one("res.users", readonly=True)
    resolved_date = fields.Datetime(readonly=True)
    can_retry = fields.Boolean(compute="_compute_can_retry")

    @api.model
    def _category_of(self, incident_type):
        """Whether ``incident_type`` is an error of the system, missing data or
        a difference a person must assess. Each processor tells it for its
        own types."""
        return "technical" if incident_type in self._retry_types() else "review"

    @api.model
    def _retry_types(self):
        """The types of the failures of a whole conversation, solved by
        processing it again."""
        return ("processing_error",)

    @api.depends("incident_type")
    def _compute_category(self):
        for incident in self:
            incident.category = self._category_of(incident.incident_type)

    @api.depends("incident_type", "state", "conversation_id.state")
    def _compute_can_retry(self):
        for incident in self:
            incident.can_retry = (
                incident.state == "open"
                and incident.incident_type in self._retry_types()
                and incident.conversation_id.state == "error"
            )

    def write(self, vals):
        res = super().write(vals)
        if vals.get("state") in ("resolved", "dismissed"):
            # Closed: the activities planned for it have nothing left to do.
            self.sudo().activity_ids.unlink()
        return res

    def _close(self, state, note=None):
        values = {
            "state": state,
            "resolved_by_id": self.env.uid,
            "resolved_date": fields.Datetime.now(),
        }
        if note:
            values["resolution_note"] = note
        self.write(values)

    def action_resolve(self):
        self.filtered(lambda i: i.state == "open")._close("resolved")

    def action_dismiss(self):
        self.filtered(lambda i: i.state == "open")._close("dismissed")

    def action_reopen(self):
        self.write({"state": "open", "resolved_by_id": False, "resolved_date": False})

    def action_retry(self):
        """Process the conversation again, once the cause is corrected."""
        for incident in self:
            if not incident.can_retry:
                raise UserError(
                    _("The incident %(name)s cannot be retried.", name=incident.name)
                )
            incident.conversation_id.action_retry()

    def action_open_conversation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mail.message.import.conversation",
            "res_id": self.conversation_id.id,
            "view_mode": "form",
        }
