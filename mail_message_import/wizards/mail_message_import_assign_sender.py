# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class MailMessageImportAssignSender(models.TransientModel):
    """Link the messages of an unknown address to a sender."""

    _name = "mail.message.import.assign.sender"
    _description = "Assign Received Messages to a Sender"

    message_ids = fields.Many2many(
        "mail.message.import.message",
        "mail_message_import_assign_sender_message_rel",
        "wizard_id",
        "message_id",
        string="Messages",
    )
    sender_id = fields.Many2one(
        "mail.message.import.sender", string="Sender", required=True
    )
    authorize_address = fields.Boolean(
        string="Authorize the address",
        default=True,
        help="Later messages of the address (the phone, the email address...) "
        "will be assigned to the sender directly.",
    )
    process_messages = fields.Boolean(
        string="Process the messages",
        default=True,
        help="Process the messages as a conversation of the sender; otherwise "
        "they are ignored.",
    )
    sender_count = fields.Integer(compute="_compute_sender_count")

    @api.depends("message_ids")
    def _compute_sender_count(self):
        for wizard in self:
            wizard.sender_count = len(
                set(
                    wizard.message_ids.mapped(
                        lambda m: (m.channel_id, m.sender_address)
                    )
                )
            )

    def action_assign(self):
        self.ensure_one()
        messages = self.message_ids.filtered(lambda m: m.state == "unidentified")
        if not messages:
            raise UserError(self.env._("Select messages of unidentified senders."))
        sender = self.sender_id
        Address = self.env["mail.message.import.address"]
        for (channel, sender_address), group in messages.grouped(
            lambda m: (m.channel_id, m.sender_address)
        ).items():
            if not sender._accepts_channel(channel):
                raise UserError(
                    self.env._(
                        "The sender %(sender)s may not send messages to "
                        "%(channel)s.",
                        sender=sender.name,
                        channel=channel.name,
                    )
                )
            normalized = Address._normalize_address(
                channel.channel_type, sender_address, channel.company_id
            )
            address = Address.browse()
            if normalized:
                address = Address.search(
                    [
                        ("sender_id", "=", sender.id),
                        ("channel_type", "=", channel.channel_type),
                        ("address_normalized", "=", normalized),
                    ],
                    limit=1,
                )
            if self.authorize_address and not address:
                address = Address.create(
                    {
                        "sender_id": sender.id,
                        "channel_type": channel.channel_type,
                        "address": sender_address,
                        "name": group[:1].sender_name,
                    }
                )
            for message in group.sorted(lambda m: (m.message_date, m.id)):
                message.sudo()._link_sender(sender, address)
                if self.process_messages:
                    self.env["mail.message.import.conversation"]._add_message(
                        message.sudo()
                    )
                else:
                    message.sudo().state = "ignored"
        return {"type": "ir.actions.act_window_close"}
