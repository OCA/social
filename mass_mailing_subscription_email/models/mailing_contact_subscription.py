# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import hashlib
import hmac

from werkzeug.urls import url_encode

from odoo import api, models, tools


class MailingContactSubscription(models.Model):
    _inherit = "mailing.contact.subscription"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda r: not r.opt_out)._send_mail_notification()
        return records

    def write(self, vals):
        changed_records = (
            self.filtered(lambda rec: rec.opt_out != vals["opt_out"])
            if "opt_out" in vals
            else None
        )
        res = super().write(vals)
        if changed_records:
            changed_records._send_mail_notification()
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

    def _unsubscribe_token(self):
        """Generate a secure hash for this mailing list and parameters"""
        # NOTE: similar to core's mailing.mailing._unsubscribe_token
        secret = self.env["ir.config_parameter"].sudo().get_param("database.secret")
        token = (
            self.env.cr.dbname,
            self.id,
            tools.ustr(self.contact_id.email_normalized),
        )
        return hmac.new(
            secret.encode("utf-8"), repr(token).encode("utf-8"), hashlib.sha512
        ).hexdigest()

    def _get_unsubscribe_url(self):
        """Generate a secure URL to opt-out of this subscription"""
        self.ensure_one()
        if not self.contact_id.email_normalized:
            return False
        params = {
            "email": self.contact_id.email_normalized,
            "token": self._unsubscribe_token(),
        }
        return "/mail/mailing/contact/%(res_id)s/unsubscribe?%(params)s" % {
            "res_id": self.id,
            "params": url_encode(params),
        }
