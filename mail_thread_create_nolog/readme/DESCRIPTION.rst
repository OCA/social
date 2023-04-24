This module will block the creation in the database of 'Record created' messages
on data models inheriting from `mail.thread`, but will instead generate this
message on the fly when Odoo displays the messages of a record.

This allows to reduce the size of the `mail_message` table.
