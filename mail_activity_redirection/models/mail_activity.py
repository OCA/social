# Copyright 2021 DEC SARL, Inc - All Rights Reserved.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api

import logging

_logger = logging.getLogger(__name__)


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.multi
    def _link_to_mail_activity_redirection(self, redirection):
        """ Keep only some references to activities redirected by this
            `redirection`.
        """
        history_activity_ids = self.env['mail.activity']
        if redirection and self:
            history_activity_ids = self
            existing_activity_ids = redirection.activity_ids.sorted(
                key=lambda r: r.id, reverse=True
            )
            for existing_activity_id in existing_activity_ids:
                if len(history_activity_ids) >= 5:
                    break
                history_activity_ids += existing_activity_id
            # Use sudo since normal user don't have write access
            redirection.sudo().activity_ids = history_activity_ids
