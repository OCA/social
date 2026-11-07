# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailMessageImportAddress(models.Model):
    """An address allowed to send messages on behalf of a sender.

    What an address is depends on its channel: a phone for WhatsApp, an email
    address for email... Each channel module tells how its addresses are
    written and compared (``_normalize_address``), so a message is identified
    the same way whatever its channel.
    """

    _name = "mail.message.import.address"
    _description = "Authorized Address"
    _order = "sender_id, id"
    _rec_name = "address"

    sender_id = fields.Many2one(
        "mail.message.import.sender",
        string="Sender",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="sender_id.company_id", store=True)
    channel_type = fields.Selection(
        selection="_selection_channel_type",
        string="Channel",
        default=lambda self: self.env[
            "mail.message.import.channel"
        ]._default_channel_type(),
    )
    name = fields.Char(string="Label", help="Who uses the address, e.g. 'Ana, buyer'.")
    address = fields.Char(
        required=True,
        help="Phone in international format for WhatsApp (+34 600 000 000), email "
        "address for email...",
    )
    address_normalized = fields.Char(
        string="Normalized address",
        compute="_compute_address_normalized",
        store=True,
        index=True,
        help="The address as the channel identifies the senders.",
    )
    active = fields.Boolean(default=True)
    authorized_date = fields.Datetime(default=fields.Datetime.now, readonly=True)

    _sql_constraints = [
        (
            "sender_address_uniq",
            "unique(sender_id, channel_type, address_normalized)",
            "This address is already authorized for the sender.",
        ),
    ]

    @api.model
    def _selection_channel_type(self):
        return (
            self.env["mail.message.import.channel"]
            ._fields["channel_type"]
            ._description_selection(self.env)
        )

    @api.model
    def _normalize_address(self, channel_type, address, company):
        """``address`` as ``channel_type`` identifies a sender, or ``""`` when it
        is not valid. Each channel module normalizes its own addresses."""
        return (address or "").strip().lower()

    def _invalid_address_message(self):
        """Why the address is not valid. Each channel module explains its format."""
        self.ensure_one()
        return _("The address %(address)s is not valid.", address=self.address)

    @api.depends("address", "name")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"{record.address} ({record.name})" if record.name else record.address
            )

    @api.depends("address", "channel_type", "sender_id.company_id.country_id")
    def _compute_address_normalized(self):
        for record in self:
            record.address_normalized = (
                self._normalize_address(
                    record.channel_type, record.address, record.sender_id.company_id
                )
                or False
            )

    @api.constrains("address_normalized", "active", "sender_id", "channel_type")
    def _check_unique_scope(self):
        """An address cannot identify two senders of the same company."""
        for record in self.filtered(lambda r: r.active and r.sender_id.active):
            if not record.address_normalized:
                raise ValidationError(record._invalid_address_message())
            others = self.sudo().search(
                [
                    ("channel_type", "=", record.channel_type),
                    ("address_normalized", "=", record.address_normalized),
                    ("sender_id", "!=", record.sender_id.id),
                    ("sender_id.active", "=", True),
                ]
            )
            for other in others:
                if record.sender_id._scope_overlaps(other.sender_id):
                    raise ValidationError(
                        _(
                            "The address %(address)s is already authorized for "
                            "another sender of the company. An address must "
                            "identify a single sender.",
                            address=record.address,
                        )
                    )

    @api.model
    def _find_for_sender(self, channel, address):
        """Authorized addresses of a sender for a channel."""
        normalized = self._normalize_address(
            channel.channel_type, address, channel.company_id
        )
        if not normalized:
            return self.browse()
        addresses = self.sudo().search(
            [
                ("channel_type", "=", channel.channel_type),
                ("address_normalized", "=", normalized),
                ("sender_id.active", "=", True),
            ]
        )
        return addresses.filtered(lambda a: a.sender_id._accepts_channel(channel))
