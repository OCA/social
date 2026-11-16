Up to 16.0 this module added the tracking of many2many and one2many fields.
Since 17.0, Odoo tracks them natively, so the module was not migrated
([#1359](https://github.com/OCA/social/pull/1359),
[#1465](https://github.com/OCA/social/pull/1465),
[#1466](https://github.com/OCA/social/pull/1466)). Odoo only stores the
names of the records, though, so this module now keeps the part that Odoo
does not cover: the ids.
