# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Edit QWeb email templates",
    "version": "8.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Hidden",
    "summary": "Glue module to enable the wysiwyg editor for qweb email "
    "templates",
    "depends": [
        'website_mail',
        'email_template_qweb',
    ],
    "data": [
        'views/templates.xml',
    ],
    "auto_install": True,
}
