This module was written to allow users to drag&drop emails from their desktop to Odoo.

It supports as well RFC822 .eml files as Outlook .msg (those only if `an extra library <https://github.com/mattgwwalker/msg-extractor>`_ is installed) files.

When the mail is dropped to an odoo record, it will automatically send a notification
of that new message that has been added to all the existing followers. It is possible
to disable this notification.
