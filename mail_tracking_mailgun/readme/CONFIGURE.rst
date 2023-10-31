To configure this module, you need to:

#. Go to Mailgun, create an account and validate your sending domain.
#. Go back to Odoo.
#. Go to *Settings > General Settings > Discuss > Enable mail tracking with Mailgun*.
#. Fill all the values. The only one required is the API key.
#. Optionally click *Unregister Mailgun webhooks* and accept.
#. Click *Register Mailgun webhooks*.

You can also config timeout for mailgun with this system parameter:

- `mailgun.timeout`: Set it to a number of seconds.
