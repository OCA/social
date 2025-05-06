In Odoo mails it is often unclear who where the other recipients of mails
received, or what the actual mail addresses where of mails sent.

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

For technical reasons this module depends on mail_composer_cc_bcc:

* We need the email_bcc field on mail.mail;
* The module mail_composer_bcc fundamentally changes the workings of the _send()
  method on mail.mail. In order not to have to support both methods depending
  on whether mail_composer_bcc is installed or not, it is easier to just make sure
  it is installed.
