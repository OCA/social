# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    @api.model_create_multi
    def create(self, vals_list):
        # Overridden to not create 'Record created' messages that increase
        # the size of 'mail_message' table for little value.
        # Instead a message will be generated on the fly when the Odoo client
        # will retrieve the list of messages for a given record.
        return super(MailThread, self.with_context(mail_create_nolog=True)).create(
            vals_list
        )
