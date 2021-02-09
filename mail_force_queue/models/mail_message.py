# -*- coding: utf-8 -*-
# Copyright 2018 Lorenzo Battistini - Agile Business Group
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, api


class Message(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, values):
        if self.env.user.company_id.force_mail_queue:
            mail_notify_force_send = self.env.context.get(
                'mail_notify_force_send', False)
            return super(Message, self.with_context(
                mail_notify_force_send=mail_notify_force_send)).create(values)
        else:
            return super(Message, self).create(values)
