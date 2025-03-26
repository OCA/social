# Copyright 2023 Solvti sp. z o.o. (https://solvti.pl).
# Copyright 2025 Therp BV (https://therp.nl).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class Alias(models.Model):
    _inherit = "mail.alias"

    @api.depends("alias_name")
    def _compute_alias_domain(self):
        alias_with_domain = self.filtered(
            lambda r: r.alias_name and "__at__" in r.alias_name
        )
        for alias in alias_with_domain:
            alias.alias_domain = alias.alias_name.split("__at__")[1]
        alias_without_domain = self - alias_with_domain
        if alias_without_domain:
            super(Alias, alias_without_domain)._compute_alias_domain()
        return None

    alias_entry = fields.Char(
        help="This will be used to enter an email, complete with domain",
    )

    @api.model
    def search(self, domain, **kwargs):
        """If mail alias in context, return this as result."""
        matching_alias = self.env.context.get("matching_alias", False)
        if matching_alias:
            return matching_alias
        return super().search(domain, **kwargs)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._patch_alias_vals(vals)
        records = super().create(vals_list)
        records._synchronize_alias_entry_with_name()
        return records

    def write(self, vals):
        self._patch_alias_vals(vals)
        result = super().write(vals)
        self._synchronize_alias_entry_with_name()
        return result

    def _synchronize_alias_entry_with_name(self):
        """In case alias created/written without alias_entry, complete entry field."""
        for this in self:
            if not this.alias_name:
                alias_entry = False
            elif "__at__" in this.alias_name:
                alias_entry = this.alias_name.replace("__at__", "@")
            else:
                alias_entry = this.alias_name
            if this.alias_entry != alias_entry:
                super(Alias, this).write({"alias_entry": alias_entry})
        return None

    @api.model
    def _patch_alias_vals(self, vals):
        """If vals contains alias_entry, add corresponding alias_name."""
        alias_entry = vals.get("alias_entry", False)
        if alias_entry:
            default_domain = self._get_default_domain()
            if "@" not in alias_entry:
                alias_name = alias_entry
            elif default_domain and default_domain in alias_entry:
                alias_name = alias_entry.split("@")[0]
            else:
                alias_name = alias_entry.replace("@", "__at__")
            vals["alias_name"] = alias_name

    @api.model
    def _get_default_domain(self):
        """get default domain."""
        ICP = self.env["ir.config_parameter"].sudo()
        return ICP.get_param("mail.catchall.domain")

    @api.model
    def get_clean_email(self, email):
        """Users tend to pollute emails with extra info. get just the email."""
        # In Odoo 17.0 there is a new method parse_contact_from_email in
        # odoo/tools/mail.py that we could use for this purpose.
        if email:
            # 1. Replace special characters with spaces.
            cleaned = (
                email.replace('"', " ")
                .replace("<", " ")
                .replace(">", " ")
                .replace(",", " ")
            )
            # 2. Split on whitespace
            parts = cleaned.split()
            # 3. Find the part with an '@' if any and assume it is the real email.
            for part in parts:
                if "@" in part:
                    return part.lower()
        return False  # Else module partner_email_check would raise ValidationError.
