# -*- coding: utf-8 -*-
# Copyright 2018 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class BaseConfigSettings(models.TransientModel):
    _inherit = 'base.config.settings'

    force_mail_queue = fields.Boolean(
        related="company_id.force_mail_queue", string="Force Mail queue",
        help="Force outgoing emails to be queued instead of sent immediately. "
             "Queued emails are sent by 'Email Queue Manager' cron")
