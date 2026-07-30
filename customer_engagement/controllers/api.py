import logging
from functools import wraps

from odoo import http
from odoo.exceptions import AccessDenied, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


def api_key_required(permission="read"):
    """
    Decorator to require API key authentication.

    :param permission: Required permission ('read', 'write', 'webhook')
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get API key from header
            api_key = request.httprequest.headers.get("X-API-Key")
            if not api_key:
                api_key = request.httprequest.headers.get("Authorization", "").replace(
                    "Bearer ", ""
                )

            try:
                # Authenticate
                api_key_record = (
                    request.env["engage.api.key"].sudo()._authenticate(api_key)
                )

                # Check permission
                channel_type = kwargs.get("channel_type") or kwargs.get("channel")
                api_key_record.check_permission(permission, channel_type)

                # Store API key in request for later use
                request.engage_api_key = api_key_record

                return func(self, *args, **kwargs)

            except AccessDenied as e:
                return self._error_response(str(e), 401)
            except Exception:
                _logger.exception("API authentication error")
                return self._error_response("Authentication failed", 401)

        return wrapper

    return decorator


class EngageAPI(http.Controller):
    """REST API for Customer Engagement."""

    # ==================== Helper Methods ====================

    def _json_response(self, data, status=200):
        """Return JSON response."""
        return request.make_json_response(data, status=status)

    def _error_response(self, message, status=400, code=None):
        """Return error JSON response."""
        return request.make_json_response(
            {
                "error": {
                    "code": code or status,
                    "message": message,
                }
            },
            status=status,
        )

    def _success_response(self, data=None, message=None):
        """Return success JSON response."""
        response = {"success": True}
        if message:
            response["message"] = message
        if data is not None:
            response["data"] = data
        return self._json_response(response)

    def _get_json_body(self):
        """Get JSON body from request."""
        try:
            return request.get_json_data()
        except Exception:
            return {}

    # ==================== Webhook Endpoints ====================

    @http.route(
        "/api/v1/webhook/message",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    @api_key_required(permission="webhook")
    def webhook_message(self, **kwargs):
        """
        Receive incoming message from external channel.

        Expected payload:
        {
            "channel": "whatsapp",
            "message_id": "external_msg_id",
            "from": {
                "id": "+5511999999999",
                "name": "John Doe"
            },
            "type": "text",
            "content": {
                "text": "Hello!",
                "media_url": "https://...",
                "media_type": "image"
            },
            "timestamp": "2024-01-15T10:30:00Z",
            "reply_to": "previous_msg_id",
            "metadata": {}
        }
        """
        try:
            data = self._get_json_body()

            channel_type = data.get("channel")
            if not channel_type:
                return self._error_response("Channel type is required", 400)

            # Extract sender info
            sender = data.get("from", {})
            sender_id = sender.get("id")
            sender_name = sender.get("name")

            if not sender_id:
                return self._error_response("Sender ID is required", 400)

            # Find or create partner
            Partner = request.env["res.partner"].sudo()
            partner = Partner._find_or_create_by_channel(
                channel_type, sender_id, sender_name
            )

            # Find or create conversation
            Conversation = request.env["engage.conversation"].sudo()
            conversation = Conversation.search(
                [
                    ("partner_id", "=", partner.id),
                    ("channel_type", "=", channel_type),
                    ("closed", "=", False),
                ],
                limit=1,
                order="create_date desc",
            )

            if not conversation:
                # Create new conversation
                conversation = Conversation.create(
                    {
                        "partner_id": partner.id,
                        "channel_type": channel_type,
                        "channel_identifier": sender_id,
                        "subject": f"Conversation with {partner.name}",
                    }
                )

            # Process content
            content = data.get("content", {})
            message_text = content.get("text", "")
            media_url = content.get("media_url")
            media_type = content.get("media_type")

            # Build message body
            body = message_text
            if media_url and not message_text:
                body = f"[{media_type or 'Media'}]"

            # Create message
            message_vals = {
                "body": body,
                "message_type": "comment",
                "subtype_id": request.env.ref("mail.mt_comment").id,
                "author_id": partner.id,
                "model": "engage.conversation",
                "res_id": conversation.id,
                # Engage-specific fields
                "channel_message_id": data.get("message_id"),
                "engage_channel_type": channel_type,
                "media_url": media_url,
                "media_type": media_type,
                "channel_metadata": data.get("metadata"),
            }

            # Handle reply-to
            if data.get("reply_to"):
                reply_msg = (
                    request.env["mail.message"]
                    .sudo()
                    ._get_message_by_channel_id(data["reply_to"], channel_type)
                )
                if reply_msg:
                    message_vals["reply_to_message_id"] = reply_msg.id

            message = request.env["mail.message"].sudo().create(message_vals)

            # Update conversation
            conversation.write(
                {
                    "write_date": message.date,
                }
            )

            return self._success_response(
                {
                    "conversation_id": conversation.id,
                    "conversation_uuid": conversation.uuid,
                    "message_id": message.id,
                    "partner_id": partner.id,
                }
            )

        except ValidationError as e:
            return self._error_response(str(e), 400)
        except Exception:
            _logger.exception("Error processing webhook message")
            return self._error_response("Internal server error", 500)

    @http.route(
        "/api/v1/webhook/status",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    @api_key_required(permission="webhook")
    def webhook_status(self, **kwargs):
        """
        Receive delivery status update for a message.

        Expected payload:
        {
            "message_id": "external_msg_id",
            "status": "delivered",
            "timestamp": "2024-01-15T10:30:00Z",
            "error": "optional error message"
        }
        """
        try:
            data = self._get_json_body()

            message_id = data.get("message_id")
            if not message_id:
                return self._error_response("Message ID is required", 400)

            status = data.get("status")
            if status not in ("sent", "delivered", "read", "failed"):
                return self._error_response("Invalid status", 400)

            # Find message
            message = (
                request.env["mail.message"]
                .sudo()
                ._get_message_by_channel_id(message_id)
            )
            if not message:
                return self._error_response("Message not found", 404)

            # Update status
            message._update_delivery_status(
                status,
                data.get("timestamp"),
                data.get("error"),
            )

            return self._success_response({"message_id": message.id})

        except Exception:
            _logger.exception("Error processing status webhook")
            return self._error_response("Internal server error", 500)

    # ==================== Conversation Endpoints ====================

    @http.route(
        "/api/v1/conversations",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    @api_key_required(permission="read")
    def list_conversations(self, **kwargs):
        """
        List conversations with optional filters.

        Query params:
        - channel: Filter by channel type
        - status: Filter by status (open, closed)
        - partner_id: Filter by partner
        - limit: Max results (default 50)
        - offset: Pagination offset
        """
        try:
            domain = []

            # Apply filters
            if kwargs.get("channel"):
                domain.append(("channel_type", "=", kwargs["channel"]))
            if kwargs.get("status") == "open":
                domain.append(("closed", "=", False))
            elif kwargs.get("status") == "closed":
                domain.append(("closed", "=", True))
            if kwargs.get("partner_id"):
                domain.append(("partner_id", "=", int(kwargs["partner_id"])))

            limit = min(int(kwargs.get("limit", 50)), 100)
            offset = int(kwargs.get("offset", 0))

            conversations = (
                request.env["engage.conversation"]
                .sudo()
                .search(domain, limit=limit, offset=offset, order="write_date desc")
            )

            data = []
            for conv in conversations:
                data.append(
                    {
                        "id": conv.id,
                        "uuid": conv.uuid,
                        "subject": conv.subject,
                        "channel_type": conv.channel_type,
                        "partner": {
                            "id": conv.partner_id.id,
                            "name": conv.partner_id.name,
                        }
                        if conv.partner_id
                        else None,
                        "stage": {
                            "id": conv.stage_id.id,
                            "code": conv.stage_id.code,
                            "name": conv.stage_id.name,
                        }
                        if conv.stage_id
                        else None,
                        "user_id": conv.user_id.id if conv.user_id else None,
                        "closed": conv.closed,
                        "create_date": conv.create_date.isoformat()
                        if conv.create_date
                        else None,
                        "write_date": conv.write_date.isoformat()
                        if conv.write_date
                        else None,
                    }
                )

            return self._success_response(data)

        except Exception:
            _logger.exception("Error listing conversations")
            return self._error_response("Internal server error", 500)

    @http.route(
        "/api/v1/conversations/<int:conversation_id>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    @api_key_required(permission="read")
    def get_conversation(self, conversation_id, **kwargs):
        """Get conversation details with messages."""
        try:
            conversation = (
                request.env["engage.conversation"].sudo().browse(conversation_id)
            )
            if not conversation.exists():
                return self._error_response("Conversation not found", 404)

            # Get messages
            messages = (
                request.env["mail.message"]
                .sudo()
                .search(
                    [
                        ("model", "=", "engage.conversation"),
                        ("res_id", "=", conversation_id),
                    ],
                    order="date asc",
                )
            )

            message_data = []
            for msg in messages:
                message_data.append(
                    {
                        "id": msg.id,
                        "body": msg.body,
                        "author": {
                            "id": msg.author_id.id,
                            "name": msg.author_id.name,
                        }
                        if msg.author_id
                        else None,
                        "date": msg.date.isoformat() if msg.date else None,
                        "message_type": msg.message_type,
                        "channel_message_id": msg.channel_message_id,
                        "delivery_status": msg.delivery_status,
                        "media_url": msg.media_url,
                        "media_type": msg.media_type,
                    }
                )

            data = {
                "id": conversation.id,
                "uuid": conversation.uuid,
                "subject": conversation.subject,
                "channel_type": conversation.channel_type,
                "channel_identifier": conversation.channel_identifier,
                "partner": {
                    "id": conversation.partner_id.id,
                    "name": conversation.partner_id.name,
                    "email": conversation.partner_id.email,
                    "phone": conversation.partner_id.phone,
                }
                if conversation.partner_id
                else None,
                "stage": {
                    "id": conversation.stage_id.id,
                    "code": conversation.stage_id.code,
                    "name": conversation.stage_id.name,
                }
                if conversation.stage_id
                else None,
                "user": {
                    "id": conversation.user_id.id,
                    "name": conversation.user_id.name,
                }
                if conversation.user_id
                else None,
                "team": {
                    "id": conversation.team_id.id,
                    "name": conversation.team_id.name,
                }
                if conversation.team_id
                else None,
                "priority": conversation.priority,
                "closed": conversation.closed,
                "create_date": conversation.create_date.isoformat()
                if conversation.create_date
                else None,
                "first_response_at": conversation.first_response_at.isoformat()
                if conversation.first_response_at
                else None,
                "resolved_at": conversation.resolved_at.isoformat()
                if conversation.resolved_at
                else None,
                "messages": message_data,
            }

            return self._success_response(data)

        except Exception:
            _logger.exception("Error getting conversation")
            return self._error_response("Internal server error", 500)

    @http.route(
        "/api/v1/conversations/<int:conversation_id>/send",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    @api_key_required(permission="write")
    def send_message(self, conversation_id, **kwargs):
        """
        Send a message to a conversation.

        Expected payload:
        {
            "text": "Message content",
            "media_url": "https://...",
            "media_type": "image"
        }
        """
        try:
            conversation = (
                request.env["engage.conversation"].sudo().browse(conversation_id)
            )
            if not conversation.exists():
                return self._error_response("Conversation not found", 404)

            data = self._get_json_body()
            text = data.get("text", "")
            media_url = data.get("media_url")
            media_type = data.get("media_type")

            if not text and not media_url:
                return self._error_response("Message text or media is required", 400)

            # Create message
            body = text
            if media_url and not text:
                body = f"[{media_type or 'Media'}]"

            message = conversation.message_post(
                body=body,
                message_type="comment",
            )

            # Update engage-specific fields
            message.sudo().write(
                {
                    "engage_channel_type": conversation.channel_type,
                    "media_url": media_url,
                    "media_type": media_type,
                    "delivery_status": "pending",
                }
            )

            return self._success_response(
                {
                    "message_id": message.id,
                    "conversation_id": conversation.id,
                }
            )

        except Exception:
            _logger.exception("Error sending message")
            return self._error_response("Internal server error", 500)

    # ==================== Partner Endpoints ====================

    @http.route(
        "/api/v1/partners/lookup",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    @api_key_required(permission="read")
    def lookup_partner(self, **kwargs):
        """
        Look up a partner by channel identifier.

        Query params:
        - channel: Channel type (whatsapp, telegram, etc.)
        - identifier: Channel-specific identifier
        """
        try:
            channel = kwargs.get("channel")
            identifier = kwargs.get("identifier")

            if not channel or not identifier:
                return self._error_response("Channel and identifier are required", 400)

            partner = (
                request.env["res.partner"]
                .sudo()
                ._find_by_channel_id(channel, identifier)
            )

            if not partner:
                return self._success_response(None)

            data = {
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "phone": partner.phone,
                "mobile": partner.mobile,
                "whatsapp_number": partner.whatsapp_number,
                "telegram_id": partner.telegram_id,
                "instagram_id": partner.instagram_id,
                "vip_customer": partner.vip_customer,
                "engage_blocked": partner.engage_blocked,
                "conversation_count": partner.engage_conversation_count,
                "open_conversations": partner.open_conversation_count,
            }

            return self._success_response(data)

        except Exception:
            _logger.exception("Error looking up partner")
            return self._error_response("Internal server error", 500)

    # ==================== Health Check ====================

    @http.route(
        "/api/v1/health",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def health_check(self, **kwargs):
        """Health check endpoint (no auth required)."""
        return self._success_response(
            {
                "status": "healthy",
                "service": "customer_engagement",
            }
        )
