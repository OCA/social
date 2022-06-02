# Go to Configuration > Technical > Emails > Templates
# Open the desired ``email.template`` record.
# In Advanced Parameters tab, find the Force Layout field.

You can leave it empty to use the default email layout (chosen by Odoo).
You can force a custom email layout of your own.
You can use the *Mail: No-Layout notification template* to prevent Odoo
from adding a layout.

To configure a custom layout of your own, some technical knowledge is needed.
You can see how the existing layouts are defined for details or inspiration:

* ``mail.mail_notification_light``
* ``mail.mail_notification_paynow``
* ``mail.mail_notification_borders``
