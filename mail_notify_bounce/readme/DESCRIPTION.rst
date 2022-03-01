This module allows, in case of bounced email messages retrieved by fetchmail,
to notify senders of original message.
Also, it is possible to configure email addresses to be notified about bounced emails.

Typical use case:

 - User configures a partner with a wrong email address
 - User sends a message to that partner
 - User gets notified about wrong email address

In some cases, these messages are silently discarded by Odoo, so users don't know about possible failures.
Even when bounce messages are correctly fetched, the sender, or other people, will not be notified.
