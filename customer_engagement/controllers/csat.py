"""CSAT Public Controller for Customer Engagement.

This module provides public endpoints for CSAT survey submission.
"""

from odoo import http
from odoo.http import request


class CSATController(http.Controller):
    """Controller for public CSAT survey access."""

    @http.route(
        "/csat/<string:token>",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def csat_form(self, token, **kwargs):
        """Display CSAT survey form."""
        survey = (
            request.env["engage.csat"].sudo().search([("token", "=", token)], limit=1)
        )

        if not survey:
            return request.render(
                "customer_engagement.csat_not_found",
                {"error": "Survey not found"},
            )

        if survey.state == "answered":
            return request.render(
                "customer_engagement.csat_already_answered",
                {"survey": survey},
            )

        if survey.state == "expired":
            return request.render(
                "customer_engagement.csat_expired",
                {"survey": survey},
            )

        return request.render(
            "customer_engagement.csat_form",
            {
                "survey": survey,
                "conversation": survey.conversation_id,
                "agent": survey.user_id,
            },
        )

    @http.route(
        "/csat/<string:token>/submit",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        sitemap=False,
        csrf=True,
    )
    def csat_submit(self, token, **kwargs):
        """Submit CSAT survey response."""
        survey = (
            request.env["engage.csat"].sudo().search([("token", "=", token)], limit=1)
        )

        if not survey:
            return request.render(
                "customer_engagement.csat_not_found",
                {"error": "Survey not found"},
            )

        # Get rating from form
        rating = kwargs.get("rating")
        if not rating or rating not in ["1", "2", "3", "4", "5"]:
            return request.render(
                "customer_engagement.csat_form",
                {
                    "survey": survey,
                    "conversation": survey.conversation_id,
                    "agent": survey.user_id,
                    "error": "Please select a rating",
                },
            )

        # Get optional fields
        feedback = kwargs.get("feedback", "").strip()
        resolved = kwargs.get("resolved") == "on"
        helpful = kwargs.get("helpful") == "on"
        recommend = kwargs.get("recommend") == "on"

        # Submit response
        result = survey.action_submit_response(
            rating=rating,
            feedback=feedback or None,
            resolved=resolved,
            helpful=helpful,
            recommend=recommend,
        )

        if result.get("success"):
            return request.render(
                "customer_engagement.csat_thank_you",
                {"survey": survey, "rating": rating},
            )
        else:
            return request.render(
                "customer_engagement.csat_form",
                {
                    "survey": survey,
                    "conversation": survey.conversation_id,
                    "agent": survey.user_id,
                    "error": result.get("error", "An error occurred"),
                },
            )

    @http.route(
        "/csat/api/<string:token>",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def csat_api_submit(self, token, rating, feedback=None, **kwargs):
        """API endpoint for CSAT submission (for mobile apps, etc.)."""
        survey = (
            request.env["engage.csat"].sudo().search([("token", "=", token)], limit=1)
        )

        if not survey:
            return {"success": False, "error": "Survey not found"}

        return survey.action_submit_response(
            rating=rating,
            feedback=feedback,
            **kwargs,
        )
