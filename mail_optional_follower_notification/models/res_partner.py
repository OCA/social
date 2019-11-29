# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _notify(self, message, rdata, record, force_send=False,
                send_after_commit=True, model_description=False,
                mail_auto_delete=True):
        if self.env.context.get('force_partners_to_notify'):
            partners_to_notify =\
                self.env.context.get('force_partners_to_notify')
            record = self.filtered(lambda p: p.id in partners_to_notify)
        return super()._notify(
            message, rdata, record,
            force_send=force_send, send_after_commit=send_after_commit,
            model_description=model_description,
            mail_auto_delete=mail_auto_delete)
