In your mail tracking status screens (explained on module *mail_tracking*), you
will see a more accurate information, like the 'Received' or 'Bounced' status,
which are not usually detected by normal SMTP servers.

It's also possible to make some checks to the partner's email addresses against
the Mailgun API:

- Check if the partner's email is in Mailgun's bounced list.
- Check the validity of the partner's mailbox.
- Force the partner's email into Mailgun's bounced list or delete from it.

It's also possible to manually check a message mailgun tracking when the webhook
couldn't be captured. For that, go to that message tracking form, press the
button *Check Mailgun*. It's important to note that tracking events have quite a
short lifespan, so after 24h they won't be recoverable.
