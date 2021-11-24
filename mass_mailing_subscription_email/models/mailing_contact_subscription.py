# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MailingContactSubscription(models.Model):
    _inherit = "mailing.contact.subscription"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda r: not r.opt_out)._send_mail_notification()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "opt_out" in vals:
            self._send_mail_notification()
        return res

    def unlink(self):
        to_unsubscribe = self.filtered(lambda r: not r.opt_out)
        to_unsubscribe._send_mail_notification(force_opt_out=True)
        return super().unlink()

    def _send_mail_notification(self, force_opt_out=None):
        if self.env.context.get("skip_subscription_email"):
            return
        for rec in self:
            opt_out = rec.opt_out if force_opt_out is None else force_opt_out
            template = (
                rec.list_id.unsubscribe_template_id
                if opt_out
                else rec.list_id.subscribe_template_id
            )
            if template:
                template.send_mail(rec.id)
