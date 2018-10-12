# -*- coding: utf-8 -*-
{
    'name': "Force From sender to be the Admin user",
    'author': "Daniel Reis,Odoo Community Association (OCA)",
    'summary': 'Force the header Sender and envelope From '
               'to a fixed outgoing address.',
    'description': """
    Sends all outgoing emails from the same fixed email address.
    The email address to use is configured in the
    System parameter "mail.from.force".
    This email is used in the email from, along with the
    actual name of the user triggering the email.

    For more details on why this may be needed, see:
    https://github.com/odoo/odoo/issues/3347
    """,
    'category': 'Mail',
    'version': '8.0.1.0.0',
    'license': 'AGPL-3',
    'depends': [
        'mail',
    ],
}
