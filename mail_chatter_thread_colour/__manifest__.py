# Copyright 2022 CreuBlanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mail Chatter Thread Colour",
    "summary": """
        Allow to change the colour of threads""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "CreuBlanca,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "depends": ["mail"],
    "data": [
        "data/ir_config_parameter_data.xml",
        "views/res_config_settings.xml",
        "views/ir_model.xml",
        "templates/assets.xml",
    ],
    "qweb": ["static/src/xml/thread.xml"],
}
