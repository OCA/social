To configure this module, you need to:

1.  Go to Mailgun, create an account and validate your sending domain.
2.  Go back to Odoo.
3.  Go to *Settings \> General Settings \> Discuss \> Enable mail
    tracking with Mailgun*.
4.  Fill all the values. The only one required is the API key.
5.  Optionally click *Unregister Mailgun webhooks* and accept.
6.  Click *Register Mailgun webhooks*.

You can also config timeout for mailgun with this system parameter:

- `mailgun.timeout`: Set it to a number of seconds.
