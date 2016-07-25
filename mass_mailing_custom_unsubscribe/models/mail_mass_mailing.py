# -*- coding: utf-8 -*-
# © 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from hashlib import sha256
from uuid import uuid4
from openerp import api, models


class MailMassMailing(models.Model):
    _inherit = "mail.mass_mailing"

    @api.model
    def _init_salt_create(self):
        """Create a salt to secure the unsubscription URLs."""
        icp = self.env["ir.config_parameter"]
        key = "mass_mailing.salt"
        salt = icp.get_param(key)
        if salt is False:
            salt = str(uuid4())
            icp.set_param(key, salt, ["base.group_erp_manager"])

    @api.model
    def hash_create(self, mailing_id, res_id, email):
        """Create a secure hash to know if the unsubscription is trusted.

        :return None/str:
            Secure hash, or ``None`` if the system parameter is empty.
        """
        salt = self.env["ir.config_parameter"].sudo().get_param(
            "mass_mailing.salt")
        if not salt:
            return None
        source = (self.env.cr.dbname, mailing_id, res_id, email, salt)
        return sha256(",".join(map(unicode, source))).hexdigest()
