import hashlib
import secrets

from odoo import api, fields, models
from odoo.exceptions import AccessDenied


class EngageApiKey(models.Model):
    """API Key for external channel integrations."""

    _name = "engage.api.key"
    _description = "Engage API Key"
    _order = "name"

    name = fields.Char(
        string="Name",
        required=True,
        help="Descriptive name for this API key",
    )
    key_hash = fields.Char(
        string="Key Hash",
        required=True,
        copy=False,
        help="SHA-256 hash of the API key",
    )
    key_prefix = fields.Char(
        string="Key Prefix",
        size=8,
        copy=False,
        help="First 8 characters of the key for identification",
    )
    active = fields.Boolean(default=True)

    # Permissions
    channel_types = fields.Selection(
        selection=[
            ("all", "All Channels"),
            ("whatsapp", "WhatsApp Only"),
            ("telegram", "Telegram Only"),
            ("instagram", "Instagram Only"),
            ("messenger", "Messenger Only"),
            ("api", "API Only"),
        ],
        string="Allowed Channels",
        default="all",
        required=True,
    )
    can_read = fields.Boolean(
        string="Can Read",
        default=True,
        help="Can query conversations and messages",
    )
    can_write = fields.Boolean(
        string="Can Write",
        default=True,
        help="Can create/update conversations and send messages",
    )
    can_receive_webhooks = fields.Boolean(
        string="Can Receive Webhooks",
        default=True,
        help="Can receive incoming message webhooks",
    )

    # Rate limiting
    rate_limit_per_minute = fields.Integer(
        string="Rate Limit (per minute)",
        default=60,
        help="Maximum API calls per minute (0 = unlimited)",
    )
    rate_limit_per_day = fields.Integer(
        string="Rate Limit (per day)",
        default=10000,
        help="Maximum API calls per day (0 = unlimited)",
    )

    # Statistics
    last_used_at = fields.Datetime(string="Last Used")
    total_requests = fields.Integer(string="Total Requests", default=0)
    requests_today = fields.Integer(
        string="Requests Today",
        compute="_compute_requests_today",
    )

    # Expiration
    expires_at = fields.Datetime(
        string="Expires At",
        help="Leave empty for no expiration",
    )

    # Webhook configuration
    webhook_url = fields.Char(
        string="Webhook URL",
        help="URL to send delivery status updates",
    )
    webhook_secret = fields.Char(
        string="Webhook Secret",
        help="Secret for webhook signature verification",
    )

    # Associated team (optional)
    team_id = fields.Many2one(
        comodel_name="engage.team",
        string="Team",
        help="Associate this key with a specific team",
    )

    _sql_constraints = [
        (
            "key_prefix_unique",
            "UNIQUE(key_prefix)",
            "API key prefix must be unique",
        ),
    ]

    def _compute_requests_today(self):
        """Compute requests made today."""
        # This would typically query a log table
        # For now, return 0 as placeholder
        for key in self:
            key.requests_today = 0

    @api.model
    def generate_key(self, name, **kwargs):
        """
        Generate a new API key.

        :param name: Name for the API key
        :param kwargs: Additional field values
        :return: tuple (api_key_record, plain_key)
        """
        # Generate a secure random key
        plain_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        key_prefix = plain_key[:8]

        vals = {
            "name": name,
            "key_hash": key_hash,
            "key_prefix": key_prefix,
            **kwargs,
        }

        record = self.create(vals)
        return record, plain_key

    @api.model
    def _authenticate(self, api_key):
        """
        Authenticate an API key.

        :param api_key: Plain text API key
        :return: engage.api.key record
        :raises: AccessDenied if invalid or expired
        """
        if not api_key:
            raise AccessDenied("API key is required")

        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:8]

        # Find matching key
        api_key_record = self.search(
            [
                ("key_hash", "=", key_hash),
                ("key_prefix", "=", key_prefix),
                ("active", "=", True),
            ],
            limit=1,
        )

        if not api_key_record:
            raise AccessDenied("Invalid API key")

        # Check expiration
        if (
            api_key_record.expires_at
            and api_key_record.expires_at < fields.Datetime.now()
        ):
            raise AccessDenied("API key has expired")

        # Update last used
        api_key_record.sudo().write(
            {
                "last_used_at": fields.Datetime.now(),
                "total_requests": api_key_record.total_requests + 1,
            }
        )

        return api_key_record

    def check_permission(self, permission, channel_type=None):
        """
        Check if this API key has a specific permission.

        :param permission: 'read', 'write', or 'webhook'
        :param channel_type: Optional channel type to check
        :return: True if permitted
        :raises: AccessDenied if not permitted
        """
        self.ensure_one()

        # Check channel permission
        if channel_type and self.channel_types != "all":
            if self.channel_types != channel_type:
                raise AccessDenied(
                    f"API key not authorized for channel: {channel_type}"
                )

        # Check operation permission
        if permission == "read" and not self.can_read:
            raise AccessDenied("API key does not have read permission")
        if permission == "write" and not self.can_write:
            raise AccessDenied("API key does not have write permission")
        if permission == "webhook" and not self.can_receive_webhooks:
            raise AccessDenied("API key does not have webhook permission")

        return True

    def action_regenerate_key(self):
        """Regenerate the API key (returns new plain key via wizard)."""
        self.ensure_one()
        # Generate new key
        plain_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        key_prefix = plain_key[:8]

        self.write(
            {
                "key_hash": key_hash,
                "key_prefix": key_prefix,
            }
        )

        # Return action to show the new key
        return {
            "type": "ir.actions.act_window",
            "name": "New API Key Generated",
            "res_model": "engage.api.key.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_api_key_id": self.id,
                "default_plain_key": plain_key,
            },
        }


class EngageApiKeyWizard(models.TransientModel):
    """Wizard to display newly generated API key."""

    _name = "engage.api.key.wizard"
    _description = "API Key Display Wizard"

    api_key_id = fields.Many2one(
        comodel_name="engage.api.key",
        string="API Key Record",
        readonly=True,
    )
    plain_key = fields.Char(
        string="API Key",
        readonly=True,
        help="Copy this key now - it cannot be retrieved later!",
    )

    def action_close(self):
        return {"type": "ir.actions.act_window_close"}
