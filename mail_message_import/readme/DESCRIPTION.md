This module gives Odoo an inbox for the messages that the company receives by
several channels (email, WhatsApp...), whatever the channel:

- **Receiving channels**: the email addresses or phone numbers where the
  messages arrive. Each channel is a module (for example
  `mail_message_import_email` or `mail_message_import_whatsapp`).
- **Senders** and their **authorized addresses**: the phones and email
  addresses allowed to send messages on behalf of each sender. A message from
  any other address waits in *Unknown senders* until a person assigns it to a
  sender, and the address can be authorized at the same time.
- **Conversations**: the consecutive messages of a sender are grouped and
  processed together once the sender has been silent for some minutes, so that
  clarifications and corrections are read in context. The conversations are
  queued, retried when they fail and reported as **incidents** when they keep
  failing.
- A **panel** with a card per receiving channel: unknown senders, incidents,
  conversations with errors or being processed, and the messages of the last
  days.

The module does not decide what a conversation means: other modules process
them (for example to turn the documents received into orders). Without one,
the conversations are just closed once grouped.
