# -*- coding: utf-8 -*-
# © 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
from odoo import api, models
_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_route(
        self, message, message_dict, model=None, thread_id=None,
        custom_values=None
    ):
        if message['Auto-Submitted'] and message['Auto-Submitted'] != 'no':
            if self._message_route_drop_autoreply(
                    message, message_dict, model=model, thread_id=thread_id,
                    custom_values=custom_values
            ):
                return []
        return super(MailThread, self).message_route(
            message, message_dict, model=model, thread_id=thread_id,
            custom_values=custom_values
        )

    @api.model
    def _message_route_drop_autoreply(
        self, message, message_dict, model=None, thread_id=None,
        custom_values=None
    ):
        """React on an autoreply, return True if the mail should be dropped,
        False otherwise"""
        _logger.info(
            'ignoring email %s from %s because it seems to be an auto '
            'reply', message.get('Message-ID'), message.get('From'),
        )
        return True
