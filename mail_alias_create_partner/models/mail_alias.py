# Copyright 2025 Hunki Enterprises BV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)

from odoo import api, exceptions, fields, models
from odoo.tools.mail import email_split_tuples
from odoo.tools.safe_eval import const_eval


class MailAlias(models.Model):
    _inherit = "mail.alias"

    alias_create_partner = fields.Boolean(
        "Create partner",
        help="Check this if you want a new partner to be created when a mail to this "
        "alias arrives from an unknown sender",
    )
    alias_create_partner_defaults = fields.Text(
        help="Defaults used to create new partners"
    )

    @api.constrains("alias_create_partner_defaults")
    def _check_alias_create_partner_defaults(self):
        for this in self.filtered("alias_create_partner_defaults"):
            try:
                const_eval(this.alias_create_partner_defaults)
            except Exception as e:
                raise exceptions.ValidationError(str(e)) from e

    def _alias_create_partner(self, msg_dict):
        """
        Create a partner based on an incoming message for which no partner was found
        """
        values = self._alias_create_partner_values(msg_dict)
        return (
            self.env["res.partner"].create(values)
            if values
            else self.env["res.partner"]
        )

    def _alias_create_partner_values(self, msg_dict):
        """
        Return values to create a partner based on self and msg_dict
        """
        mail_tuples = email_split_tuples(msg_dict.get("email_from", ""))
        if not mail_tuples:
            return {}
        [(name, email)] = mail_tuples[:1]
        values = const_eval(self.alias_create_partner_defaults or "{}")
        values.update(name=name or email, email=email)
        return values
