Delete email notifications in error.

The scheduled action *Notification: Delete Notifications older than 6
Month* provided by Odoo is responsible to delete notifications that have
been sent successfully.

However, it doesn't delete the notifications that could not be sent, and
their number could keep growing over time, impacting the performance of
some queries related to the chatter.

This module extends the scheduled action of Odoo to also delete such
notifications.
