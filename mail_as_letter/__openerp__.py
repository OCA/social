# -*- coding: utf-8 -*-
# Copyright 2016 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Mail As Letter',
    'summary': """
        This module allows to download a mail message as a pdf letter.""",
    'version': '9.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'ACSONE SA/NV,Odoo Community Association (OCA)',
    'website': 'www.acsone.eu',
    'depends': [
        'mail',
    ],
    'data': [
        'wizards/mail_compose_message.xml',
        'report/mail_as_letter_qweb.xml',
    ],
    'demo': [
    ],
}
