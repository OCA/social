1. Give the group *Message Import Manager* to the users that manage the
   application (the administrator has it after the installation).
2. Install the module of a channel (email, WhatsApp...) and create its receiving
   channel in *Message Import > Configuration > Receiving channels*.
3. In *Message Import > Configuration > Senders*, create the senders and the
   phones or email addresses they send from, in the tab *Phones and email
   addresses*.
4. In *Message Import > Configuration > Settings*, set the minutes without new
   messages before a conversation is processed, and the attempts before it is
   left in error.

Forwarded Outlook emails (`.msg`) are unpacked when the Python library
`extract-msg` is installed; standard emails (`.eml`) need nothing else.
