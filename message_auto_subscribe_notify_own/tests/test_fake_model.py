# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# Copyright 2019 Aleph Objects, Inc.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class MessageAutoSubscribeNotifyOwnTest(models.Model):
    """A Fake model to Test."""

    _name = 'message_auto_subscribe_notify_own.test'
    _description = 'Message Auto Subscribe Notify Own Test'
    _inherit = 'mail.thread'

    name = fields.Char()
    user_id = fields.Many2one(
        comodel_name='res.users',
        track_visibility='onchange',
    )
