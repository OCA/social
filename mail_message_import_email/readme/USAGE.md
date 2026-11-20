- The emails appear in *Message Import > Received > Received messages* with the
  type *Email* and their subject. The filter *Email* shows only them.
- Each email is one message: an email that arrives twice (same
  `Message-Id`) is received once.
- Every email that reaches the mailbox is a message of the channel, even when
  it replies to a document of Odoo or is also sent to an alias.
- A reply to a received email is a new message of the conversation, not a note
  on the previous one: it is how the senders correct what they sent.
- The files of a message are the attachments of the email, except the images
  smaller than 20 KB (logos and icons of the signatures) and the copy of the
  original email. The forwarded emails (`.eml`, `.msg`) are unpacked as in the
  other channels.
- The module sends no email.
