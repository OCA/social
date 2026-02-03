"""Customer Satisfaction Survey for Customer Engagement.

This module provides CSAT (Customer Satisfaction) survey functionality
for gathering feedback after conversations are resolved.
"""

import uuid
from datetime import timedelta

from odoo import api, fields, models


class EngageCSAT(models.Model):
    """Customer Satisfaction Survey."""

    _name = "engage.csat"
    _description = "Customer Satisfaction Survey"
    _order = "create_date desc"

    # Reference
    conversation_id = fields.Many2one(
        "engage.conversation",
        required=True,
        ondelete="cascade",
        string="Conversation",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        related="conversation_id.partner_id",
        store=True,
        string="Customer",
    )
    user_id = fields.Many2one(
        "res.users",
        related="conversation_id.user_id",
        store=True,
        string="Agent",
    )
    team_id = fields.Many2one(
        "engage.team",
        related="conversation_id.team_id",
        store=True,
        string="Team",
    )

    # Token for public access
    token = fields.Char(
        required=True,
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        index=True,
    )
    access_url = fields.Char(
        compute="_compute_access_url",
        string="Survey URL",
    )

    # Timing
    sent_at = fields.Datetime(
        default=fields.Datetime.now,
        string="Sent At",
    )
    expires_at = fields.Datetime(
        compute="_compute_expires_at",
        store=True,
        string="Expires At",
    )
    answered_at = fields.Datetime(
        string="Answered At",
    )
    response_time = fields.Float(
        compute="_compute_response_time",
        store=True,
        string="Response Time (hours)",
    )

    # Rating
    rating = fields.Selection(
        [
            ("1", "1 - Very Unsatisfied"),
            ("2", "2 - Unsatisfied"),
            ("3", "3 - Neutral"),
            ("4", "4 - Satisfied"),
            ("5", "5 - Very Satisfied"),
        ],
        string="Rating",
    )
    rating_value = fields.Integer(
        compute="_compute_rating_value",
        store=True,
        string="Rating Value",
    )
    feedback = fields.Text(
        string="Feedback",
    )

    # Categories
    resolved_satisfactorily = fields.Boolean(
        string="Issue Resolved",
    )
    agent_helpful = fields.Boolean(
        string="Agent Was Helpful",
    )
    would_recommend = fields.Boolean(
        string="Would Recommend",
    )

    # State
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("answered", "Answered"),
            ("expired", "Expired"),
        ],
        default="pending",
        string="State",
        index=True,
    )

    # Configuration
    expiry_days = fields.Integer(
        default=7,
        string="Expiry Days",
    )

    @api.depends("token")
    def _compute_access_url(self):
        """Compute the public access URL for the survey."""
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for record in self:
            record.access_url = f"{base_url}/csat/{record.token}"

    @api.depends("sent_at", "expiry_days")
    def _compute_expires_at(self):
        """Compute expiration date."""
        for record in self:
            if record.sent_at:
                record.expires_at = record.sent_at + timedelta(days=record.expiry_days)
            else:
                record.expires_at = False

    @api.depends("rating")
    def _compute_rating_value(self):
        """Convert rating selection to integer for calculations."""
        for record in self:
            record.rating_value = int(record.rating) if record.rating else 0

    @api.depends("sent_at", "answered_at")
    def _compute_response_time(self):
        """Compute time between sending and answering."""
        for record in self:
            if record.sent_at and record.answered_at:
                delta = record.answered_at - record.sent_at
                record.response_time = delta.total_seconds() / 3600
            else:
                record.response_time = 0.0

    def action_send(self):
        """Send the CSAT survey to the customer."""
        self.ensure_one()
        if not self.conversation_id.partner_id.email:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Cannot Send Survey",
                    "message": "Customer has no email address.",
                    "type": "warning",
                },
            }

        # Send email
        template = self.env.ref(
            "customer_engagement.email_template_csat_survey",
            raise_if_not_found=False,
        )
        if template:
            template.send_mail(self.id, force_send=True)

        self.write(
            {
                "state": "sent",
                "sent_at": fields.Datetime.now(),
            }
        )

        return True

    def action_submit_response(self, rating, feedback=None, **kwargs):
        """Submit survey response (called from public controller)."""
        self.ensure_one()

        # Check if already answered or expired
        if self.state == "answered":
            return {"success": False, "error": "Survey already answered"}
        if self.state == "expired" or (
            self.expires_at and fields.Datetime.now() > self.expires_at
        ):
            self.state = "expired"
            return {"success": False, "error": "Survey has expired"}

        # Save response
        vals = {
            "rating": str(rating),
            "feedback": feedback,
            "answered_at": fields.Datetime.now(),
            "state": "answered",
        }

        # Additional fields
        if "resolved" in kwargs:
            vals["resolved_satisfactorily"] = kwargs["resolved"]
        if "helpful" in kwargs:
            vals["agent_helpful"] = kwargs["helpful"]
        if "recommend" in kwargs:
            vals["would_recommend"] = kwargs["recommend"]

        self.write(vals)

        # Notify agent if low rating
        if int(rating) <= 2 and self.user_id:
            self._notify_low_rating()

        return {"success": True}

    def _notify_low_rating(self):
        """Notify agent about low rating."""
        self.ensure_one()
        self.user_id.notify_warning(
            title="Low CSAT Rating Received",
            message=f"Conversation {self.conversation_id.uuid[:8]} received a {self.rating}-star rating.",
        )

    @api.model
    def _cron_check_expired(self):
        """Mark expired surveys."""
        expired = self.search(
            [
                ("state", "in", ["pending", "sent"]),
                ("expires_at", "<", fields.Datetime.now()),
            ]
        )
        expired.write({"state": "expired"})

    @api.model
    def create_for_conversation(self, conversation, auto_send=False):
        """Create a CSAT survey for a resolved conversation."""
        # Check if survey already exists
        existing = self.search(
            [("conversation_id", "=", conversation.id)],
            limit=1,
        )
        if existing:
            return existing

        survey = self.create({"conversation_id": conversation.id})

        if auto_send:
            survey.action_send()

        return survey


class EngageConversationCSAT(models.Model):
    """Extend conversation with CSAT fields."""

    _inherit = "engage.conversation"

    csat_ids = fields.One2many(
        "engage.csat",
        "conversation_id",
        string="Satisfaction Surveys",
    )
    csat_rating = fields.Integer(
        compute="_compute_csat",
        store=True,
        string="CSAT Rating",
    )
    csat_feedback = fields.Text(
        compute="_compute_csat",
        store=True,
        string="CSAT Feedback",
    )
    csat_sent = fields.Boolean(
        compute="_compute_csat",
        store=True,
        string="CSAT Sent",
    )

    @api.depends("csat_ids.rating_value", "csat_ids.feedback", "csat_ids.state")
    def _compute_csat(self):
        """Compute CSAT fields from surveys."""
        for conv in self:
            answered = conv.csat_ids.filtered(lambda c: c.state == "answered")
            if answered:
                # Get latest answered survey
                latest = answered.sorted("answered_at", reverse=True)[:1]
                conv.csat_rating = latest.rating_value
                conv.csat_feedback = latest.feedback
                conv.csat_sent = True
            else:
                conv.csat_rating = 0
                conv.csat_feedback = False
                conv.csat_sent = bool(conv.csat_ids)

    def action_send_csat(self):
        """Send CSAT survey for this conversation."""
        self.ensure_one()
        survey = self.env["engage.csat"].create_for_conversation(self, auto_send=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Survey Sent",
                "message": f"CSAT survey sent to {self.partner_id.name}",
                "type": "success",
            },
        }

    def action_view_csat(self):
        """View CSAT surveys for this conversation."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Satisfaction Surveys",
            "res_model": "engage.csat",
            "view_mode": "tree,form",
            "domain": [("conversation_id", "=", self.id)],
            "context": {"default_conversation_id": self.id},
        }
