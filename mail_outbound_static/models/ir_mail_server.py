# Copyright 2017 LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import re
from email.utils import formataddr, parseaddr

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError


class IrMailServer(models.Model):

    _inherit = "ir.mail_server"

    smtp_from = fields.Char(
        string="Email From",
        help="Set this in order to email from a specific address."
        " If the original message's 'From' does not match with the domain"
        " whitelist then it is replaced with this value. If does match with the"
        " domain whitelist then the original message's 'From' will not change",
    )
    domain_whitelist = fields.Char(
        help="Allowed Domains list separated by commas. If there is not given"
        " SMTP server it will let us to search the proper mail server to be"
        " used to sent the messages where the message 'From' email domain"
        " match with the domain whitelist."
    )

    @api.constrains("domain_whitelist")
    def check_valid_domain_whitelist(self):
        if self.domain_whitelist:
            domains = list(self.domain_whitelist.split(","))
            for domain in domains:
                if not self._is_valid_domain(domain):
                    raise ValidationError(
                        _(
                            "%s is not a valid domain. Please define a list of"
                            " valid domains separated by comma"
                        )
                        % (domain)
                    )

    @api.constrains("smtp_from")
    def check_valid_smtp_from(self):
        if self.smtp_from:
            match = re.match(
                r"^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\."
                r"[a-z]{2,4})$",
                self.smtp_from,
            )
            if match is None:
                raise ValidationError(_("Not a valid Email From"))

    def _is_valid_domain(self, domain_name):
        domain_regex = (
            r"(([\da-zA-Z])([_\w-]{,62})\.){,127}(([\da-zA-Z])"
            r"[_\w-]{,61})?([\da-zA-Z]\.((xn\-\-[a-zA-Z\d]+)|([a-zA-Z\d]{2,})))"
        )
        domain_regex = "{}$".format(domain_regex)
        valid_domain_name_regex = re.compile(domain_regex, re.IGNORECASE)
        domain_name = domain_name.lower().strip()
        return True if re.match(valid_domain_name_regex, domain_name) else False

    @api.model
    def _get_domain_whitelist(self, domain_whitelist_string):
        res = domain_whitelist_string.split(",") if domain_whitelist_string else []
        res = [item.strip() for item in res]
        return res

    @api.model
    def send_email(
        self, message, mail_server_id=None, smtp_server=None, *args, **kwargs
    ):
        # Get email_from and name_from
        if message["From"].count("<") > 1:
            split_from = message["From"].rsplit(" <", 1)
            name_from = split_from[0]
            email_from = split_from[-1].replace(">", "")
        else:
            name_from, email_from = parseaddr(message["From"])

        email_domain = email_from.split("@")[1]

        # Replicate logic from core to get mail server
        # Get proper mail server to use
        if not smtp_server and not mail_server_id:
            mail_server_id = self._get_mail_sever(email_domain)

        # If not mail sever defined use smtp_from defined in odoo config
        if mail_server_id:
            mail_server = self.sudo().browse(mail_server_id)
            domain_whitelist = mail_server.domain_whitelist
            smtp_from = mail_server.smtp_from
        else:
            domain_whitelist = tools.config.get("smtp_domain_whitelist")
            smtp_from = tools.config.get("smtp_from")

        domain_whitelist = self._get_domain_whitelist(domain_whitelist)

        # Replace the From only if needed
        if smtp_from and (not domain_whitelist or email_domain not in domain_whitelist):
            email_from = formataddr((name_from, smtp_from))
            message.replace_header("From", email_from)
            bounce_alias = (
                self.env["ir.config_parameter"].sudo().get_param("mail.bounce.alias")
            )
            if not bounce_alias:
                # then, bounce handling is disabled and we want
                # Return-Path = From
                if "Return-Path" in message:
                    message.replace_header("Return-Path", email_from)
                else:
                    message.add_header("Return-Path", email_from)

        return super(IrMailServer, self).send_email(
            message, mail_server_id, smtp_server, *args, **kwargs
        )

    @tools.ormcache("email_domain")
    def _get_mail_sever(self, email_domain):
        """return the mail server id that match with the domain_whitelist
        If not match then return the default mail server id available one"""
        mail_server_id = None
        for item in self.sudo().search(
            [("domain_whitelist", "!=", False)], order="sequence"
        ):
            domain_whitelist = self._get_domain_whitelist(item.domain_whitelist)
            if email_domain in domain_whitelist:
                mail_server_id = item.id
                break
        if not mail_server_id:
            mail_server_id = self.sudo().search([], order="sequence", limit=1).id
        return mail_server_id

    @api.model_create_multi
    def create(self, vals_list):
        self.clear_caches()
        return super().create(vals_list)

    def write(self, values):
        self.clear_caches()
        return super().write(values)

    def unlink(self):
        self.clear_caches()
        return super().unlink()
