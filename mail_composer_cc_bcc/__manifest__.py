# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Email CC and BCC",
    "summary": "This module enables sending mail to CC and BCC partners in mail composer form.",  # noqa: E501
    "version": "17.0.1.0.0",
    "development_status": "Alpha",
    "category": "Social",
    "website": "https://github.com/OCA/social",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "maintainers": ["trisdoan"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "preloadable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "views/res_company_views.xml",
        "views/mail_mail_views.xml",
        "views/mail_message_views.xml",
        "views/mail_template_views.xml",
        "wizards/mail_compose_message_view.xml",
    ],
}
