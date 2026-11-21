This module adds the **WhatsApp** channel to *Mail Message Import*
(`mail_message_import`), through the WhatsApp gateway of
`mail_gateway_whatsapp`: the senders write or forward their messages to a
WhatsApp number, and each message becomes a received message, identified,
grouped and processed as the messages of every other channel.

- A **receiving channel** of type *WhatsApp* is a number of Meta (its *Phone
  Number ID*) received by a WhatsApp gateway.
- The **authorized addresses** of type *WhatsApp* are phones, compared in
  international format as WhatsApp sends them: `+34 600 000 000`,
  `0034600000000` and, in a Spanish company, `600 000 000` are the same phone.
- Each message is a **received message**, with its text, a copy of its files
  and a link to the Discuss chat of the gateway.

The gateway keeps working as usual: it checks the signature of the webhooks,
posts the messages in its Discuss chats and downloads their files.
