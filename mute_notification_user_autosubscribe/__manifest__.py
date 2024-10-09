# Copyright 2024 Manuel Regidor <manuel.regidor@sygel.es>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Mute Notification User Autosubscribe",
    "summary": "Do not send notifications to users autosubcribed through user_id field",
    "version": "17.0.1.0.0",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "Sygel,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "data/mail_message_subtype_data.xml",
        "security/ir.model.access.csv",
        "views/user_autosubscribe_mute_views.xml",
    ],
}
