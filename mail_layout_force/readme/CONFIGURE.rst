#. Go to Settings > Technical > Emails > Templates
#. Open the desired ``email.template`` record.
#. In Advanced Parameters tab, find the Force Layout field.

You can leave it empty to use the default email layout (chosen by Odoo).
You can force a custom email layout of your own.
You can use the *Mail: No-Layout notification template* to prevent Odoo
from adding a layout.

To configure a custom layout of your own, some technical knowledge is needed.
You can see how the existing layouts are defined for details or inspiration:

* ``mail.mail_notification_light``
* ``mail.mail_notification_paynow``
* ``mail.mail_notification_borders``

To force a new custom layout for emails that do not use an existing ``email.template``
record (e.g., emails sent from the chatter):

#. Go to Settings > Technical > User Interface > Views.
#. Copy the current layout (e.g., mail.message_notification_email) to create a new one, and remove any parts you don’t need.
#. Open the layout that you want to swap with a substitute. Then, under the Layout Mapping tab:
    * Set ``Substitute Layout`` to the new custom layout you created.
    * Set ``Models`` if you want to apply the replacement only to specific models. If left empty,
      the email layout will be replaced for all models.
