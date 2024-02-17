# © 2016 Sunflower IT (http://sunflowerweb.nl)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Message Edit",
    "summary": "Edit, Delete or Move messages to any model",
    "version": "14.0.1.0.0",
    "category": "Social Network",
    "website": "https://github.com/OCA/social",
    "author": "Sunflower IT, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "mail",
        "web",
    ],
    "data": [
        "security/mail_edit_security.xml",
        "views/assets.xml",
        "views/compose_message.xml",
    ],
    "demo": ["demo/data.xml"],
    "qweb": [
        "static/src/components/message/mail_edit.xml",
    ],
}
