Force outgoing emails to be queued instead of sent immediately.
Queued emails are sent by 'Email Queue Manager' cron.

This also solves possible TransactionRollbackError while deleting outgoing email (see `https://github.com/odoo/odoo/issues/22148
<https://github.com/odoo/odoo/issues/22148>`_.)
