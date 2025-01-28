Odoo will add a default email layout on most commercial communications.

The email layout is a ``QWeb`` view that ends up wrapping the message body
when sending an email. It usually displays the related document reference,
the company logo, and a small footer saying "Powered by Odoo".

There are notably two main layouts used in Odoo, and the user can't control when
they're used, as it's hardcoded into the different applications.

* ``mail.message_notification_email``
* ``mail.mail_notification_light``
* ``mail.mail_notification_paynow``

This module allows to force a specific layout for a given ``email.template``,
effectively overwritting the one hardcoded by Odoo. Additionally, it enables
forcing a custom layout for emails that do not use an existing ``email.template``
record (e.g., when sending an email from the chatter).

This allows you to fully customize the way Odoo emails are rendered and sent
to your customers.
