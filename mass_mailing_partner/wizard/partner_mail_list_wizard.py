# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PartnerMailListWizard(models.TransientModel):
    _name = "partner.mail.list.wizard"
    _description = "Create contact mailing list"

    mail_list_id = fields.Many2one(comodel_name="mail.mass_mailing.list",
                                   string="Mailing List")
    partner_ids = fields.Many2many(
        comodel_name="res.partner", relation="mail_list_wizard_partner",
        default=lambda self: self.env.context.get("active_ids"))

    @api.multi
    def add_to_mail_list(self):
        contact_obj = self.env['mail.mass_mailing.contact']
        partners = self.partner_ids

        add_list = partners.filtered('mass_mailing_contact_ids')
        for partner in add_list:
            partner.mass_mailing_contact_ids[0].list_ids |= self.mail_list_id

        to_create = partners - add_list
        for partner in to_create:
            if not partner.email:
                raise UserError(_("Partner '%s' has no email.") % partner.name)
            contact_vals = {
                'partner_id': partner.id,
                'list_ids': [[6, 0, [self.mail_list_id.id]]],
                'title_id': partner.title or False,
                'company_name': partner.company_id.name or False,
                'country_id': partner.country_id or False,
                'tag_ids': partner.category_id or False,
            }
            contact_obj.create(contact_vals)
