# Copyright 2016 Jairo Llopis <jairo.llopis@tecnativa.com>
# Copyright 2018 David Vidal <david.vidal@tecnativa.com>
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Customizable unsubscription process on mass mailing emails",
    "summary": "Know and track (un)subscription reasons, GDPR compliant",
    "category": "Marketing",
    "version": "13.0.1.0.1",
    "depends": ["mass_mailing"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_unsubscription_reason.xml",
        "templates/general_reason_form.xml",
        "templates/mass_mailing_contact_reason.xml",
        "views/assets.xml",
        "views/mail_unsubscription_reason_view.xml",
        "views/mail_mass_mailing_list_view.xml",
        "views/mail_unsubscription_view.xml",
    ],
    "demo": ["demo/assets.xml"],
    "images": ["images/form.png"],
    "author": "Tecnativa," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "installable": True,
}
