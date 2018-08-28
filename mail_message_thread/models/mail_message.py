# -*- coding: utf-8 -*-
# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, models


class MailMessage(models.Model):

    _name = 'mail.message'
    _inherit = ['mail.message',
                'mail.thread',
                ]
    _description = 'Mail Message (Threaded)'

    @api.multi
    def message_post(self, *args, **kwargs):
        return super(
            MailMessage,
            self.with_context(mail_create_nolog=True),
        ).message_post(*args, **kwargs)
