To choose which messages count, go to *Settings > Technical > Parameters > System
Parameters* (in developer mode) and set ``mail_last_message_date.message_types`` to a
comma-separated list of message types:

* ``email``: incoming emails. Emails sent from a template outside the chatter, for
  example by a *Send Email* server action, also count; if the template has *Auto
  Delete* checked (the default), they stop counting once they are sent.
* ``comment``: messages and notes posted in the chatter
* ``notification``: system notifications, such as record creation and tracked field
  changes
* ``auto_comment``: emails sent automatically when a tracked field such as the stage
  changes

By default, ``email`` and ``comment`` count. If the parameter has no valid type, no
message counts.
