# Copyright 2022 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import smtplib

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import ustr

SMTP_TIMEOUT = 60


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def send_email(
        self, message, mail_server_id=None, smtp_server=None, *args, **kwargs
    ):
        # Replicate logic from core to get mail server
        mail_server = None
        if mail_server_id:
            mail_server = self.sudo().browse(mail_server_id)
        elif not smtp_server:
            mail_server = self.sudo().search([], order="sequence", limit=1)
        return (
            super(IrMailServer, self)
            .with_context(mail_server=mail_server)
            .send_email(message, mail_server_id, smtp_server, *args, **kwargs)
        )

    def connect(
        self,
        host=None,
        port=None,
        user=None,
        password=None,
        encryption=None,
        smtp_debug=False,
    ):
        if user and self.env.context.get("mail_server"):
            mail_server_id = self.env.context.get("mail_server")
            if encryption == "ssl":
                if not "SMTP_SSL" in smtplib.__all__:
                    raise UserError(
                        _(
                            "Your OpenERP Server does not support SMTP-over-SSL. You could use STARTTLS instead."
                            "If SSL is needed, an upgrade to Python 2.6 on the server-side should do the trick."
                        )
                    )
                connection = smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT)
            else:
                connection = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT)
            connection.set_debuglevel(smtp_debug)
            if encryption == "starttls":
                # starttls() will perform ehlo() if needed first
                # and will discard the previous list of services
                # after successfully performing STARTTLS command,
                # (as per RFC 3207) so for example any AUTH
                # capability that appears only on encrypted channels
                # will be correctly detected for next step
                connection.starttls()

            if user:
                # Attempt authentication - will raise if AUTH service not supported
                # The user/password must be converted to bytestrings in order to be usable for
                # certain hashing schemes, like HMAC.
                # See also bug #597143 and python issue #5285
                user = ustr(user).encode("utf-8")
                password = ustr(password).encode("utf-8")
                mail_server_id._smtp_login(connection, user, password)
            return connection
        else:
            return super(IrMailServer, self).connect(
                host, port, user, password, encryption, smtp_debug
            )

    def _smtp_login(self, connection, smtp_user, smtp_password):
        """Authenticate the SMTP connection.
        Can be overridden in other module for different authentication methods.Can be
        called on the model itself or on a singleton.
        :param connection: The SMTP connection to authenticate
        :param smtp_user: The user to used for the authentication
        :param smtp_password: The password to used for the authentication
        """
        connection.login(smtp_user, smtp_password)
