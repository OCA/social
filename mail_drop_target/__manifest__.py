# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Drag & drop emails to Odoo",
    "version": "16.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Discuss",
    "website": "https://github.com/OCA/social",
    "summary": "Attach emails to Odoo by dragging them from your desktop",
    "depends": ["mail"],
    "external_dependencies": {"python": ["extract_msg", "cryptography<37"]},
    "data": ["views/res_config_settings_views.xml"],
    "assets": {
        "web.assets_backend": [
            "mail_drop_target/static/src/js/file_uploader.esm.js",
        ],
    },
}
