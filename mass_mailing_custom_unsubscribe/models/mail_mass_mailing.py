# -*- coding: utf-8 -*-
# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import hmac
import hashlib
from openerp import api, models
from openerp.exceptions import AccessDenied
from openerp.tools import consteq


class MailMassMailing(models.Model):
    _inherit = "mail.mass_mailing"

    @api.multi
    def _unsubscribe_token(self, res_id, compare=None):
        """Generate a secure hash for this mailing list and parameters.
        This is appended to the unsubscription URL and then checked at
        unsubscription time to ensure no malicious unsubscriptions are
        performed.

        :param int res_id:
            ID of the resource that will be unsubscribed.

        :param str compare:
            Received token to be compared with the good one.

        :raise AccessDenied:
            Will happen if you provide :param:`compare` and it does not match
            the good token.
        """
        secret = self.env["ir.config_parameter"].sudo().get_param(
            "database.secret")
        key = (self.env.cr.dbname, self.id, int(res_id))
        token = hmac.new(str(secret), repr(key), hashlib.sha512).hexdigest()
        if compare is not None and not consteq(token, str(compare)):
            raise AccessDenied()
        return token

    @api.model
    def update_opt_out(self, mailing_id, email, res_ids, value):
        """Save unsubscription reason when opting out from mailing."""
        mailing = self.browse(mailing_id)
        if value and self.env.context.get("default_reason_id"):
            for res_id in res_ids:
                # reason_id and details are expected from the context
                self.env["mail.unsubscription"].create({
                    "email": email,
                    "mass_mailing_id": mailing.id,
                    "unsubscriber_id": "%s,%d" % (
                        mailing.mailing_model, int(res_id)),
                })
        return super(MailMassMailing, self).update_opt_out(
            mailing_id, email, res_ids, value)
