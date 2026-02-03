from odoo import api, fields, models


class MailMessage(models.Model):
    """Extension of mail.message for omnichannel engagement."""

    _inherit = "mail.message"

    # Channel identification
    channel_message_id = fields.Char(
        string="Channel Message ID",
        index=True,
        help="Original message ID from the external channel (WhatsApp, Telegram, etc.)",
    )
    engage_channel_type = fields.Selection(
        selection=[
            ("whatsapp", "WhatsApp"),
            ("telegram", "Telegram"),
            ("instagram", "Instagram"),
            ("messenger", "Messenger"),
            ("email", "Email"),
            ("livechat", "Live Chat"),
            ("api", "API"),
        ],
        string="Channel Type",
        help="The channel through which this message was sent/received",
    )

    # Delivery status (for outbound messages)
    delivery_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("read", "Read"),
            ("failed", "Failed"),
        ],
        string="Delivery Status",
        default="pending",
        help="Current delivery status of the message",
    )
    sent_at = fields.Datetime(string="Sent At")
    delivered_at = fields.Datetime(string="Delivered At")
    read_at = fields.Datetime(string="Read At")
    delivery_error = fields.Text(
        string="Delivery Error",
        help="Error message if delivery failed",
    )

    # Media attachments (beyond standard attachment_ids)
    media_url = fields.Char(
        string="Media URL",
        help="URL of media content from external channel",
    )
    media_type = fields.Selection(
        selection=[
            ("image", "Image"),
            ("audio", "Audio"),
            ("video", "Video"),
            ("document", "Document"),
            ("sticker", "Sticker"),
            ("location", "Location"),
            ("contact", "Contact"),
        ],
        string="Media Type",
    )
    thumbnail_url = fields.Char(string="Thumbnail URL")

    # Reply-to functionality
    reply_to_message_id = fields.Many2one(
        comodel_name="mail.message",
        string="Reply To",
        help="The message this is a reply to",
    )

    # Extra channel metadata
    channel_metadata = fields.Json(
        string="Channel Metadata",
        help="Additional metadata from the channel (JSON format)",
    )

    # Computed fields
    is_from_channel = fields.Boolean(
        string="From External Channel",
        compute="_compute_is_from_channel",
        store=True,
    )

    @api.depends("engage_channel_type")
    def _compute_is_from_channel(self):
        for message in self:
            message.is_from_channel = bool(message.engage_channel_type)

    def _update_delivery_status(self, status, timestamp=None, error=None):
        """
        Update delivery status via webhook.

        :param status: New status (sent, delivered, read, failed)
        :param timestamp: Optional timestamp for the status change
        :param error: Optional error message for failed status
        """
        self.ensure_one()
        vals = {"delivery_status": status}

        if not timestamp:
            timestamp = fields.Datetime.now()

        if status == "sent":
            vals["sent_at"] = timestamp
        elif status == "delivered":
            vals["delivered_at"] = timestamp
            if not self.sent_at:
                vals["sent_at"] = timestamp
        elif status == "read":
            vals["read_at"] = timestamp
            if not self.delivered_at:
                vals["delivered_at"] = timestamp
            if not self.sent_at:
                vals["sent_at"] = timestamp
        elif status == "failed":
            vals["delivery_error"] = error or "Unknown error"

        self.write(vals)

    @api.model
    def _get_message_by_channel_id(self, channel_message_id, channel_type=None):
        """
        Find a message by its external channel ID.

        :param channel_message_id: The ID from the external channel
        :param channel_type: Optional channel type filter
        :return: mail.message record or empty recordset
        """
        domain = [("channel_message_id", "=", channel_message_id)]
        if channel_type:
            domain.append(("engage_channel_type", "=", channel_type))
        return self.search(domain, limit=1)
