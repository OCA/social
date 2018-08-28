# -*- coding: utf-8 -*-
# Copyright 2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def migrate(cr, version=None):
    # initialize value for employees with values for everyone
    cr.execute(
        'update mail_message_subtype set '
        'custom_notification_mail_employees=custom_notification_mail',
    )
