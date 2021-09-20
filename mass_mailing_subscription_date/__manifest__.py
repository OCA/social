# Copyright 2021 Camptocamp (http://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Mass Mailing Subscription Date",
    "summary": "Track contact's subscription date to mailing lists",
    "version": "14.0.1.0.0",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["ivantodorovich"],
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "category": "Marketing",
    "depends": ["mass_mailing"],
    "data": ["views/mailing_contact_subscription.xml"],
    "post_init_hook": "post_init_hook",
}
