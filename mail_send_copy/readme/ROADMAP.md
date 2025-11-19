- Add the possibility to select if the mail is sent in "Cc" or in "Bcc"
  mode.
- `mail.mail` sends one email per recipient partner, so the sender
  receives one copy per recipient.
- No guard when the sender is the notifications or catchall address: the
  copy goes back to the Odoo mailbox and may loop through fetchmail.
