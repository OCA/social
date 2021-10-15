# Copyright 2017 Tecnativa - Jairo Llopis
# Copyright 2018 Tecnativa - David Vidal
# Copyright 2019 Tecnativa - Victor Martin
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Dynamic Mass Mailing Lists",
    "summary": "Mass mailing lists that get autopopulated",
    "version": "14.0.1.0.0",
    "category": "Marketing",
    "website": "https://github.com/OCA/social",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mass_mailing_partner"],
    "data": [
        "security/ir.model.access.csv",
        # This should go before "mailing_list_view.xml"
        "wizards/mailing_load_filter_views.xml",
        "views/mailing_list_view.xml",
    ],
}
