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
    partner_unique = fields.Boolean(
        string="Partner unique?",
        help="If is checked, multiple contacts cannot be linked to the same partner",
        default=True,
    )

    @api.constrains("partner_unique", "contact_ids")
    def _check_contact_ids_partner_id(self):
        contact_obj = self.env["mailing.contact"]
        for mailing_list in self.filtered("partner_unique"):
            data = contact_obj.read_group(
                [
                    ("id", "in", mailing_list.contact_ids.ids),
                    ("partner_id", "!=", False),
                ],
                ["partner_id"],
                ["partner_id"],
            )
            if len(list(filter(lambda r: r["partner_id_count"] > 1, data))):
                raise ValidationError(
                    _("A partner cannot be multiple times " "in the same list")
                )
