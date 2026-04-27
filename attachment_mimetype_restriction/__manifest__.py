# Copyright 2026 Quartile (https://www.quartile.co)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Attachment MIME Type Restriction",
    "summary": "Restrict attachment uploads to an allowlist of MIME types",
    "version": "15.0.1.0.0",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "Quartile, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "views/ir_model_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "maintainers": ["yostashiro", "aungkokolin1997"],
}
