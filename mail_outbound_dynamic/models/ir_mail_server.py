# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from odoo import api, fields, models
import odoo.tools as tools
from email.utils import parseaddr, formataddr


class IrMailServer(models.Model):

    _inherit = "ir.mail_server"

    smtp_from = fields.Char(
        string="Email From", help="Change message 'From' with this specific"
        " address if 'From' domain is different from Allowed Domain")

    allowed_domain = fields.Char(
        help="Allowed domain that can use this SMTP without changing the"
        " smtp_from")

    @api.model
    def _get_mail_sever(self, mail_server_id, smtp_server, email_domain):
        """ return: 1) if defined return this one
                    2) return the one that match with the allowed_domain
                    3) return the default available one """
        mail_server = None
        if mail_server_id:
            mail_server = self.sudo().browse(mail_server_id)
        elif not smtp_server:
            mail_server = self.sudo().search(
                [('allowed_domain', '=', email_domain)], order='sequence',
                limit=1)
            if not mail_server:
                mail_server = self.sudo().search([], order='sequence', limit=1)
        return mail_server

    @api.model
    def send_email(self, message, mail_server_id=None, smtp_server=None, *args,
                   **kwargs):
        # Get email_from and name_from
        name_from, email_from = parseaddr(message["From"])
        email_domain = email_from.split('@')[1]

        # Get proper mail server to use
        mail_server = self._get_mail_sever(mail_server_id, smtp_server,
                                           email_domain)

        # If not mail sever defined use smtp_from defined in config
        if mail_server:
            allowed_domain = mail_server.allowed_domain
            smtp_from = mail_server.smtp_from
        else:
            allowed_domain = tools.config.get('smtp_allowed_domain')
            smtp_from = tools.config.get('smtp_from')

        # Replace the From only if needed
        if smtp_from and (not allowed_domain or email_domain != allowed_domain):
            email_from = formataddr((name_from, smtp_from))
            message.replace_header('From', email_from)

        return super(IrMailServer, self).send_email(
            message, mail_server_id, smtp_server, *args, **kwargs
        )
