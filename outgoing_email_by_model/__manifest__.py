# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

{
    "name": "Outgoing Email by Model",
    "version": "15.0.1.0.0",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "Camptocamp SA, Odoo Community Association (OCA)",
    "maintainers": ["mmequignon"],
    "license": "AGPL-3",
    "installable": True,
    "auto_install": False,
    "external_dependencies": {
        "python": ["odoo_test_helper"],
    },
    "depends": [
        "mail",
    ],
    "data": [
        "views/ir_model.xml",
    ],
}
