# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "Mail Attach Existing Attachment (Account)",
    "summary": "Module to use attach existing attachment for account module",
    "author": "Pedro<xeroz.pglez@gmail.com>, Odoo Community Association (OCA), Process Control",
    "category": "Social Network",
    "version": "15.0.0.0.1",
    "license": "AGPL-3",
    "depends": ["account", "mail_attach_existing_attachment"],
    "data": ["wizard/account_invoice_send_view.xml"],
    "installable": True,
    "auto_install": False,
    "website": "https://github.com/OCA/social",
}
