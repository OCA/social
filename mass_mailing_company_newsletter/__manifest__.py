# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mass Mailing Company Newsletter",
    "summary": "Easily manage partner's subscriptions to your main mailing list.",
    "version": "14.0.1.0.1",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["ivantodorovich"],
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "category": "Marketing",
    "depends": [
        "mass_mailing",
        "mass_mailing_contact_partner",
        "mass_mailing_subscription_date",
    ],
    "data": [
        "views/res_config_settings.xml",
        "views/res_partner.xml",
    ],
}
