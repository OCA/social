# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class IrMailServer(models.Model):
    # Inherit mixin again to get enhanced version.
    _name = "ir.mail_server"
    _inherit = ["ir.mail_server", "microsoft.outlook.mixin"]

    def _smtp_login(self, connection, smtp_user, smtp_password):
        record = self._get_preset_record() if self._has_id_and_secret() else self
        return super(IrMailServer, record)._smtp_login(
            connection, smtp_user, smtp_password
        )
