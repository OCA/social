# Copyright 2018 David Juaneda - <djuaneda@sdi.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Activity Board",
    "summary": "Add Activity Boards",
    "version": "13.0.1.1.0",
    "development_status": "Beta",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "SDi, David Juaneda, ACSONE SA/NV, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["calendar", "board"],
    "data": ["views/templates.xml", "views/mail_activity_view.xml"],
    "qweb": ["static/src/xml/inherit_chatter.xml"],
}
