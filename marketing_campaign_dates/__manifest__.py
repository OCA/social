# Copyright 2026 Binhex Cloud
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Marketing Campaign Dates",
    "summary": "Add start/end dates and date-based filters to UTM campaigns",
    "version": "18.0.1.0.0",
    "category": "Marketing",
    "author": "Binhex Cloud, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "maintainers": [
        "szalatyzuzanna",
        "popadron",
    ],
    "license": "AGPL-3",
    "depends": ["utm"],
    "data": [
        "views/utm_campaign_views.xml",
    ],
    "demo": [
        "data/demo_data.xml",
    ],
    "installable": True,
}
