# Copyright 2024 NSI-SA (<http://nsi-sa.be>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = "account.move.send"

    notify_followers = fields.Boolean(default=True)

    def action_send_and_print(
        self, force_synchronous=False, allow_fallback_pdf=False, **kwargs
    ):
        self.ensure_one()
        return super(
            AccountMoveSend, self.with_context(notify_followers=self.notify_followers)
        ).action_send_and_print(force_synchronous, allow_fallback_pdf, **kwargs)
