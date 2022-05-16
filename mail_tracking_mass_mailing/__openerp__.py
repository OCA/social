# -*- coding: utf-8 -*-
# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# Copyright 2017 Vicent Cubells - <vicent.cubells@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail tracking for mass mailing",
    "summary": "Improve mass mailing email tracking",
    "version": "9.0.1.0.0",
    "category": "Social Network",
    "website": "http://www.tecnativa.com",
    "author": "Tecnativa, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    'auto_install': True,
    "depends": [
        "mass_mailing",
        "mail_tracking",
    ],
    "data": [
        "views/mail_tracking_email_view.xml",
        "views/mail_mail_statistics_view.xml",
        "views/mail_mass_mailing_view.xml",
        "views/mail_mass_mailing_contact_view.xml",
    ],
    "pre_init_hook": "pre_init_hook",
}
