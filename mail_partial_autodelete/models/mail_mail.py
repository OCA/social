# Copyright 2021 Akretion (http://www.akretion.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        self = self.with_context(autodelete_skip_unlink=True)
        return super()._send(auto_commit, raise_exception, smtp_session)

    def unlink(self):
        to_unlink = self
        if self.env.context.get("autodelete_skip_unlink"):
            to_purge = self.filtered(lambda r: r.auto_delete)
            to_purge.write({"body_html": "", "body": ""})
            to_unlink -= to_purge
        super(MailMail, to_unlink).unlink()
