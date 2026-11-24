# Copyright 2026 Binhex
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MailMessageImportSender(models.Model):
    """Who sends messages from its authorized addresses (its phones, its email
    addresses...), usually the company itself or one of its partners."""

    _name = "mail.message.import.sender"
    _description = "Sender"
    _inherit = ["mail.thread"]
    _order = "name, id"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
        help="Company that receives the messages of the sender.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        check_company=True,
        help="Contact of the sender in Odoo.",
    )
    address_ids = fields.One2many(
        "mail.message.import.address", "sender_id", string="Authorized addresses"
    )
    note = fields.Text()
    address_count = fields.Integer(compute="_compute_counters")
    message_count = fields.Integer(compute="_compute_counters")
    conversation_count = fields.Integer(compute="_compute_counters")
    open_incident_count = fields.Integer(compute="_compute_counters")

    def _compute_counters(self):
        def counts(model, domain=()):
            return dict(
                self.env[model]._read_group(
                    [("sender_id", "in", self.ids), *domain],
                    ["sender_id"],
                    ["__count"],
                )
            )

        messages = counts("mail.message.import.message")
        conversations = counts("mail.message.import.conversation")
        incidents = counts("mail.message.import.incident", [("state", "=", "open")])
        for sender in self:
            sender.address_count = len(sender.address_ids)
            sender.message_count = messages.get(sender, 0)
            sender.conversation_count = conversations.get(sender, 0)
            sender.open_incident_count = incidents.get(sender, 0)

    def write(self, vals):
        res = super().write(vals)
        if {"active", "company_id"} & set(vals):
            # The reception scope changed: an address may now be ambiguous.
            self.address_ids._check_unique_scope()
        return res

    def _scope_overlaps(self, other):
        """Whether both senders receive messages on the same channels."""
        self.ensure_one()
        return self.company_id == other.company_id

    def _accepts_channel(self, channel):
        """Whether the sender receives messages on ``channel``: the channels of
        its company."""
        self.ensure_one()
        return channel.company_id == self.company_id

    def _action_related(self, xmlid, domain, context=None):
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["domain"] = domain
        action["context"] = context or {}
        return action

    def action_view_messages(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_message",
            [("sender_id", "in", self.ids)],
        )

    def action_view_conversations(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_conversation",
            [("sender_id", "in", self.ids)],
        )

    def action_view_incidents(self):
        return self._action_related(
            "mail_message_import.action_mail_message_import_incident",
            [("sender_id", "in", self.ids)],
            {"search_default_open": 1},
        )
