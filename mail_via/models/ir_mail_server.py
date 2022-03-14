# Copyright 2019 Akretion <https://www.akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo import models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    def build_email(self, email_from, email_to, subject, body, **kwargs):
        if self.env.context.get("sender_is_via"):
            via = self.env["ir.config_parameter"].get_param("mail.via.alias")
            domain = self.env["ir.config_parameter"].get_param("mail.catchall.domain")
            original_from = email_from.replace("<", '"').replace(">", '"')
            email_from = "{} <{}@{}>".format(original_from, via, domain)
        return super().build_email(email_from, email_to, subject, body, **kwargs)
