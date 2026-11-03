This module adds the **email** channel to *Mail Message Import*
(`mail_message_import`): the senders write or forward their emails to a
receiving address, and each email becomes a received message, identified,
grouped and processed as the messages of every other channel.

- A **receiving channel** of type *Email* has a receiving address and the
  incoming mail server of Odoo that reads its mailbox.
- The **authorized addresses** of type *Email* are compared normalized: without
  the name nor the capital letters.
- Each email is a **received message** of type *Email*, with its subject, its
  headers and body as text, its attachments as files and the email itself in
  its chatter.
