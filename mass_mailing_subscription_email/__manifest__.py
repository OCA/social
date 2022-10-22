# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mass Mailing Subscription Email",
    "summary": "Send notification emails when contacts subscription changes.",
    "version": "14.0.1.0.3",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["ivantodorovich"],
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "category": "Marketing",
    "depends": ["mass_mailing"],
    "data": [
        "data/mail_template.xml",
        "views/mailing_list.xml",
    ],
    "post_init_hook": "post_init_hook",
}
