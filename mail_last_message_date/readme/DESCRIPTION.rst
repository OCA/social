This module adds a ``last_message_date`` field to every model with a chatter
(``mail.thread``): the datetime of the latest message on the record.

The field is computed from the messages when it is read, and is not stored, so
posting a message does not write to the record. It can be used in search domains,
filters and timed automated actions, but not to sort or group records in list views.
Only internal users can see it.
