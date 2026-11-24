1. Create in your mail server a mailbox only for this channel, e.g.
   `orders@company.com`. Nothing else may read it: the incoming mail server
   marks the emails as read. The catchall or a mailbox already read by another
   route of Odoo (CRM, helpdesk...) does not work: the emails would go there.
2. In *Message Import > Configuration > Receiving channels*, create a channel:
   - *Channel*: **Email**.
   - *Receiving address*: the address of the mailbox.
   - *Configure the incoming mail server* (administrators only) opens the
     incoming mail server form of Odoo with the user, IMAP over SSL, the port
     993, *Create a new record* set to *Received Message* and *Keep
     attachments*, and links the server to the channel. Fill in the server and
     the password, press *Test & Confirm* and keep the server active.
   - A server created in *Settings > Technical > Incoming Mail Servers* works
     too, if it creates *Received Message* records.
3. In each sender, tab *Phones and email addresses*, add the email addresses it
   sends from, with the channel *Email*. A new address can also be authorized
   from its first email, in *Message Import > To review > Unknown senders*.

The channel is *Pending verification* while its incoming mail server is not
confirmed or is archived: no email is read until then.

Odoo does not check who sends an email: the *From* can be forged. Let the mail
server filter the emails with the SPF, DKIM and DMARC of the domains.
