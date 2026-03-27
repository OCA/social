# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Composer Template Search",
    "version": "18.0.1.0.0",
    "category": "Social",
    "summary": "Adds an inline search bar to the mail composer template "
    "selector dropdown",
    "author": "Heliconia Solutions Pvt. Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "maintainers": ["Bhavesh Heliconia"],
    "development_status": "Alpha",
    "depends": [
        "mail",
    ],
    "assets": {
        "web.assets_backend": [
            "mail_composer_template_search/static/src/js/mail_composer_template_selector.esm.js",
            "mail_composer_template_search/static/src/xml/mail_composer_template_selector.xml",
            "mail_composer_template_search/static/src/scss/mail_composer_template_selector.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
