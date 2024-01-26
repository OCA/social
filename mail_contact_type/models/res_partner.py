# Copyright 2023 Foodles (https://www.foodles.com/)
# @author Pierre Verkest <pierreverkest84@gmail.com>
# @author Matthias Barkat <matthias.barkat@foodles.co>
# @author Alexandre Galdeano <alexandre.galdeano@foodles.co>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = "res.partner"

    mail_contact_type_ids = fields.Many2many(
        "mail.contact.type",
        string="Mail Contact Types",
        help="Used by email template to select contacts by mail contact type",
    )

    def _find_contacts_by_mail_contact_types(self, codes):
        """
        Example of usage:
        self._find_contacts_by_mail_contact_types([["customer","accounting"], "supplier"])
        return contacts that are (customer and accounting) or supplier
        """
        contacts = self.env["res.partner"].browse()
        for code_list in codes:
            if not isinstance(code_list, list):
                code_list = [code_list]
            contacts |= (
                self.commercial_partner_id.child_ids | self.commercial_partner_id
            ).filtered(
                lambda contact: all(
                    code in contact.mail_contact_type_ids.mapped("code")
                    for code in code_list
                )
            )
        return contacts

    def contact_by_types(self, *codes):
        return ",".join(
            [
                str(contact.id)
                for contact in self._find_contacts_by_mail_contact_types(codes)
            ]
        )

    def _get_name(self):
        partner = self
        name = super()._get_name()

        if (
            not self._context.get("show_mail_contact_types")
            or not partner.mail_contact_type_ids
        ):
            return name

        mail_contact_types_str = ", ".join(partner.mail_contact_type_ids.mapped("name"))

        return f"{name} ({mail_contact_types_str})"

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        partners = super()._name_search(
            name, args, operator=operator, limit=limit, name_get_uid=name_get_uid
        )
        if self._context.get("show_mail_contact_types"):
            # unfortunately odoo base overwrite _name_search and force an *AND* operator
            # between domain provide by `args` and other searching pattern added
            # by that base module so here we are running an extra request to return
            # all partners with those matching the contact type keeping same order as base
            fields = [
                field
                for field in self._get_name_search_order_by_fields().split(",")
                if field
            ]
            fields.append("display_name")
            partners = self.search(
                expression.OR(
                    [
                        [("id", "in", partners)],
                        [("mail_contact_type_ids", "=ilike", name)],
                    ]
                ),
                limit=limit,
                order=",".join(fields),
            ).ids
        return partners
