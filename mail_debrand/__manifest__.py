# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Debrand",
    "summary": "Remove Odoo branding in sent emails",
    "version": "12.0.1.0.0",
    "category": "Social Network",
    "website": "https://odoo-community.org/",
    "author": "Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "mail",
    ],
    "data": [
        'views/mail_notification_view.xml'
    ]
}
