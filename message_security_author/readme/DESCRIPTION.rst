Some modules like `mail_tracking` give the users the possibility to access to
the messages by indirect ways. Odoo have not yet regulated what the users can
do to messages because by default in Odoo no users can access to them.

Thus, this `message_security_author` module enters in scene.

This module restricts who can edit/delete messages. Specifically, a message
may be edited or deleted if and only if:

- The user is who created the message previously.
- The user have special permission (is in the group `Mail Message Manager`)
