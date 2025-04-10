# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MailingList(models.Model):
    _inherit = "mailing.list"

    partner_mandatory = fields.Boolean(string="Mandatory Partner", default=False)
    partner_category = fields.Many2one(
        comodel_name="res.partner.category", string="Partner Tag"
    )

    @api.constrains("contact_ids")
    def _check_contact_ids_partner_id(self):
        contact_obj = self.env["mailing.contact"]
        for mailing_list in self:
            data = contact_obj.read_group(
                [
                    ("id", "in", mailing_list.contact_ids.ids),
                    ("partner_id", "!=", False),
                ],
                ["partner_id"],
                ["partner_id"],
            )
            duplicates = list(filter(lambda r: r["partner_id_count"] > 1, data))
            if len(duplicates):
                duplicates_list = "\n".join(
                    [
                        f'({dup["partner_id_count"]}) [{dup["partner_id"][0]}] \
                        {str(dup["partner_id"][1])}'
                        for dup in duplicates
                    ]
                )
                raise ValidationError(
                    _(
                        "A partner cannot be multiple times in the same list\n"
                        "Duplicate contacts found:\n"
                        "%s",
                        duplicates_list,
                    )
                )
