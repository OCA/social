# -*- coding: utf-8 -*-
# © 2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Use email templates in notifications",
    "version": "8.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Social Network",
    "summary": "Allows to configure message subtypes with mail templates",
    "depends": [
        'mail',
        'email_template',
    ],
    "data": [
        "data/email_template.xml",
        "data/mail_message_subtype.xml",
        "views/mail_message_subtype.xml",
    ],
}
