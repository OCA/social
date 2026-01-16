# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Resend mass mailings",
    "version": "18.0.1.0.0",
    "category": "Marketing",
    "summary": """
        This module allows resending mass mailings with additional controls and options.
    """,
    "website": "https://github.com/OCA/social",
    "author": "Nitrokey GmbH, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": ["mass_mailing"],
    "data": [
        "views/mailing_mailing_views.xml",
    ],
    "maintainers": ["pedrobaeza"],
    "development_status": "Mature",
}
