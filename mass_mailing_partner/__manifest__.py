# Copyright 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2015-2016 Antonio Espinosa <antonio.espinosa@tecnativa.com>
# Copyright 2015 Javier Iniesta <javieria@antiun.com>
# Copyright 2020 Tecnativa - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Link partners with mass-mailing",
    "version": "17.0.1.0.0",
    "author": "Tecnativa, " "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "category": "Marketing",
    "depends": ["mass_mailing"],
    "post_init_hook": "post_init_hook",
    "data": [
        "security/ir.model.access.csv",
        "views/mailing_trace_view.xml",
        "views/mailing_contact_view.xml",
        "views/mailing_view.xml",
        "views/res_partner_view.xml",
        "wizard/partner_mail_list_wizard.xml",
    ],
    "installable": True,
}
