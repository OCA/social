This module stores the ids of the records involved in tracked changes of
many2many and one2many fields.

Odoo tracks these fields, but it only keeps the names of the records, joined
by commas, in `old_value_char` and `new_value_char`. With this module, the
ids before and after the change are also stored as a JSON list in
`old_value_text` and `new_value_text` of `mail.tracking.value` (`"[]"` when
there is no record). The names stay as Odoo stores them.

The ids make it possible to know which records were added or removed even when two
records have the same name, or when a record is renamed or archived later.

It depends on Odoo's *Discuss Tracking* (`mail_tracking`) technical module,
which stores the tracking values and shows them in Settings › Technical ›
Discuss › Tracking Values (this replaces the menu the module had up to 16.0).
