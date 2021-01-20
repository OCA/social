# Copyright 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "QWeb for email templates",
    "version": "12.0.1.1.0",
    "author": "Therp BV, "
              "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Marketing",
    "summary": "Use the QWeb templating mechanism for emails",
    'website': 'https://github.com/OCA/social',
    "depends": [
        'mail',
    ],
    "demo": [
        "demo/ir_ui_view.xml",
        "demo/mail_template.xml",
    ],
    "data": [
        "views/mail_template.xml",
    ],
    'installable': True,
}
