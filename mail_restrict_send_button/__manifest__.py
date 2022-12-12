# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Mail Restrict Send Button",
    "summary": "Security for Send Message Button on Chatter Area",
    "version": "14.0.1.1.0",
    "category": "Social Network",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "depends": ["mail"],
    "installable": True,
    "maintainer": ["dreispt"],
    "development_status": "Alpha",
    "data": ["security/res_groups.xml", "views/assets.xml"],
    "qweb": ["static/src/xml/chatter.xml"],
}
