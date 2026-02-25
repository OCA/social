# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class FetchmailServer(models.Model):
    """Add authentication for each separate server."""

    _name = "fetchmail.server"
    _inherit = ["fetchmail.server", "microsoft.outlook.mixin"]

    def _imap_login(self, connection):
        record = self._get_preset_record() if self._has_id_and_secret() else self
        return super(FetchmailServer, record)._imap_login(connection)
