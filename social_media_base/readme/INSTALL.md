This module is not compatible with the *Social Marketing* module (`social`)
of Odoo Enterprise: both declare the `social.media`, `social.account` and
`social.post` models, so they cannot live in the same database.

The manifest states it with `"excludes": ["social"]`, so Odoo refuses the
installation with an error when the other module is already installed, and
the other way round. The whole *Social Media* family is affected, since every
module of it depends on this one.
