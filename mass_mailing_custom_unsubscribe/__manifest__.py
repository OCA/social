# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# Copyright 2018 David Vidal <david.vidal@tecnativa.com>
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Customizable unsubscription process on mass mailing emails",
    "summary": "Know and track (un)subscription reasons, GDPR compliant",
    "category": "Marketing",
    "version": "15.0.1.0.0",
    "depends": ["mass_mailing"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_unsubscription_reason.xml",
        "templates/general_reason_form.xml",
        "templates/mass_mailing_contact_reason.xml",
        "views/mail_unsubscription_reason_view.xml",
        "views/mail_mass_mailing_list_view.xml",
        "views/mail_unsubscription_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            (
                "replace",
                "mass_mailing/static/src/js/unsubscribe.js",
                "mass_mailing_custom_unsubscribe/static/src/js/unsubscribe.js",
            ),
        ],
        "web.assets_tests": [
            "mass_mailing_custom_unsubscribe/static/src/js/contact.tour.esm.js",
            "mass_mailing_custom_unsubscribe/static/src/js/partner.tour.esm.js",
        ],
    },
    "demo": ["demo/assets.xml"],
    "images": ["images/form.png"],
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "installable": True,
}
