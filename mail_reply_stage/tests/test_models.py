# Copyright 2025 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TestMailReplyParent(models.Model):
    _name = "test.mail.reply.parent"

    name = fields.Char()
    stage_ids = fields.Many2many("test.mail.reply.stage")


class TestMailReply(models.Model):
    _name = "test.mail.reply"
    _inherit = ["mail.thread"]

    name = fields.Char()
    parent_id = fields.Many2one("test.mail.reply.parent")
    stage_id = fields.Many2one("test.mail.reply.stage")


class TestMailReplyStage(models.Model):
    _name = "test.mail.reply.stage"

    name = fields.Char()
