# -*- coding: utf-8 -*-
# License AGPL-3: Antiun Ingenieria S.L. - Javier Iniesta
# See README.rst file on addon root folder for more details

from openerp import models, api, fields


class EventRegistrationMailListWizard(models.TransientModel):
    _name = "event.registration.mail.list.wizard"
    _description = "Create contact mailing list"

    mail_list = fields.Many2one(comodel_name="mail.mass_mailing.list",
                                string="Mailing list")
    event_registrations = fields.Many2many(comodel_name="event.registration",
                                           relation="mail_list_wizard_event"
                                           "_registration")

    @api.multi
    def add_to_mail_list(self):
        contact_obj = self.env['mail.mass_mailing.contact']
        registration_obj = self.env['event.registration']
        for registration_id in self.env.context.get('active_ids', []):
            registration = registration_obj.browse(registration_id)
            criteria = [('email', '=', registration.email),
                        ('list_id', '=', self.mail_list.id)]
            contact_test = contact_obj.search(criteria)
            if contact_test:
                continue
            contact_vals = {
                'email': registration.email,
                'name': registration.name,
                'list_id': self.mail_list.id
            }
            contact_obj.create(contact_vals)
