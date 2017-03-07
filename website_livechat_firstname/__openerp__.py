# -*- coding: utf-8 -*-
# Copyright 2017 Specialty Medical Drugstore, LLC.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Website Live Chat - First Name",
    "summary": "Shows only the first name of the operator in the website",
    "version": "9.0.1.0.0",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "SMDrugstore, Laslabs, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "partner_firstname",
        "website_livechat",
    ],
    "data": [
        "views/website_livechat_firstname_view.xml",
    ],
    "demo": [
        "demo/res_partner_demo.xml",
    ],
}
