# -*- coding: utf-8 -*-
# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Link partners with mass-mailing",
    "version": "10.0.1.0.1",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "website": "https://www.tecnativa.com",
    "license": "AGPL-3",
    "category": "Marketing",
    "depends": [
        'mass_mailing',
    ],
    "post_init_hook": "post_init_hook",
    'data': [
        'views/mail_mail_statistics_view.xml',
        'views/mail_mass_mailing_contact_view.xml',
        'views/mail_mass_mailing_view.xml',
        'views/res_partner_view.xml',
        'wizard/partner_mail_list_wizard.xml'
    ],
    "installable": True,
}
