import hashlib

from odoo import api, fields, models


def generate_hash(value):
    mail_hash = hashlib.md5(value.encode("utf-8")).hexdigest()
    return mail_hash


class Alias(models.Model):
    _inherit = "mail.alias"

    alias_domain = fields.Char(inverse="_inverse_alias_domain", store=True,)
    alias_display_name = fields.Char()
    alias_name = fields.Char(compute="_compute_alias_name_and_hash", store=True)
    alias_hash = fields.Char(compute="_compute_alias_name_and_hash", store=True)
    check_domain = fields.Boolean(
        help=(
            "Determines whether alias should be processed together with domain.\n"
            "If checked domain will be taken into account during mail processing.\n\n"
            "Alias name is genereted as follow: 'HASH+alias_name'\n\n"
            "*HASH = hash(alias_display_name + alias_domain)"
        ),
    )

    def _inverse_alias_domain(self):
        pass

    @api.depends("alias_domain", "alias_display_name", "check_domain", "alias_name")
    def _compute_alias_name_and_hash(self):
        for rec in self:
            if rec.check_domain and rec.alias_display_name and rec.alias_domain:
                alias_hash = generate_hash(rec.alias_display_name + rec.alias_domain)
                rec.alias_hash = alias_hash
                rec.alias_name = alias_hash + "+" + rec.alias_display_name
            elif rec.alias_name or rec.alias_display_name:
                name = rec.alias_display_name or rec.alias_name
                rec.alias_hash = False
                rec.alias_name = rec.alias_display_name = rec._clean_and_make_unique(
                    name, alias_ids=rec.ids
                )
            else:
                rec.alias_hash = rec.alias_name = False

    def write(self, vals):
        name = vals.get("alias_name") or vals.get("alias_display_name")
        if name and not vals.get("check_domain") and not self.check_domain:
            vals["alias_name"] = vals[
                "alias_display_name"
            ] = self._clean_and_make_unique(name, alias_ids=self.ids)
        if vals.get("check_domain") is False:
            vals["alias_domain"] = (
                self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")
            )
        return super().write(vals)
