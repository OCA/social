# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from imaplib import IMAP4, IMAP4_SSL

from odoo import api, models


class FetchmailServer(models.Model):
    _inherit = "fetchmail.server"

    @api.multi
    def connect(self):
        self.ensure_one()
        if self.type == "imap":
            if self.is_ssl:
                connection = IMAP4_SSL(self.server, int(self.port))
            else:
                connection = IMAP4(self.server, int(self.port))
            self._imap_login(connection)
        elif self.type == "pop":
            super(FetchmailServer, self).connect()
        return connection

    def _imap_login(self, connection):
        """Authenticate the IMAP connection.
        Can be overridden in other module for different authentication methods.
        :param connection: The IMAP connection to authenticate
        """
        self.ensure_one()
        connection.login(self.user, self.password)
