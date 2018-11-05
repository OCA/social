You must configure Mailgun webhooks in order to receive mail events:

1. Got a Mailgun account and validate your sending domain.
2. Go to Webhook tab and configure the below URL for each event:

.. code:: html

   https://<your_domain>/mail/tracking/all/<your_database>

Replace '<your_domain>' with your Odoo install domain name
and '<your_database>' with your database name.

In order to validate Mailgun webhooks you have to configure the following system
parameters:

- `mailgun.apikey`: You can find Mailgun api_key in your validated sending
  domain.
- `mailgun.api_url`: It should be fine as it is, but it could change in the
  future.
- `mailgun.domain`: In case your sending domain is different from the one
  configured in `mail.catchall.domain`.
- `mailgun.validation_key`: If you want to be able to check mail address
  validity you must config this parameter with your account Public Validation
  Key.

You can also config partner email autocheck with this system parameter:

- `mailgun.auto_check_partner_email`: Set it to True.
