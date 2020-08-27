# Copyright 2017 David BEAL @ Akretion
# Copyright 2019 Camptocamp SA

# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Mail Inline CSS",
    "summary": "Convert style tags in inline style in your mails",
    "version": "13.0.1.0.1",
    "author": "Akretion, camptocamp, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/social",
    "license": "AGPL-3",
    "category": "Tools",
    "installable": True,
    "external_dependencies": {"python": ["premailer"]},
    "depends": ["email_template_qweb"],
    "demo": ["demo/demo_template.xml", "demo/demo_mail_template.xml"],
}
