# -*- coding: utf-8 -*-
# © 2016 Antiun Ingeniería S.L. - Jairo Llopis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Responsive Layout Snippets for Writing Emails",
    "summary": "Well... pseudo-responsive (see description)",
    "version": "8.0.2.1.0",
    "category": "Marketing",
    "website": "http://www.antiun.com",
    "author": "Antiun Ingeniería S.L., Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "images": [
        "images/snippets.png",
    ],
    "depends": [
        "website_mail_snippet_vertical_resize_base",
    ],
    "data": [
        "views/res_config_view.xml",
        "views/templates.xml",
        "views/snippet_1_col.xml",
        "views/snippet_2_cols.xml",
        "views/snippet_3_cols.xml",
        "views/snippet_event_date.xml",
        "views/snippet_hr.xml",
        "views/snippet_img_text.xml",
        "views/snippet_text_img.xml",
    ],
}
