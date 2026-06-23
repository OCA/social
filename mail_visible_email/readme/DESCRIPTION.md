In Odoo mails it is often unclear who were the other recipients of mails
received, or what the actual mail addresses were of mails sent.
 
This module adds the following fields to mail_message:
 
- email_to
- email_cc
- email_bcc
 
For both incoming and outgoing mails, the actual to and cc headers
from the mails will be stored here. For outgoing mails also the bcc
header.
 
In case we receive a mail because we received it on an address that was
in the bcc of the email sent, the address will actually be shown on the
email_to field. This is because there is no bcc header in an incoming mail,
we will have the address in the Delivered-To header.
 
Note that we will only store the unadorned email (without partner name),
as this will be the relevant part, and the partner names are visible on
other fields.
 
As of Odoo 18, ``email_to`` and ``email_cc`` are native fields on
``mail.mail``, so this module no longer depends on ``mail_composer_cc_bcc``.
The ``email_bcc`` field is added to ``mail.mail`` by this module itself.
 
