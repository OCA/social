# -*- coding: utf-8 -*-
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Email Snippets Background Color Picker",
    "summary": "Set any background color for any mail editor snippet",
    "version": "8.0.1.0.0",
    "category": "Marketing",
    "website": "http://www.antiun.com",
    "author": "Antiun Ingeniería S.L., Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "images": [
        "images/click_option.png",
        "images/color_picker.png",
        "images/color_set.png",
    ],
    "depends": [
        "website_mail",
    ],
    "data": [
        "views/assets.xml",
        "views/snippets.xml",
    ],
}
