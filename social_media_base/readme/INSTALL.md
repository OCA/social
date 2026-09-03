This module is not compatible with the *Social Marketing* module (`social`)
of Odoo Enterprise: both declare the `social.media`, `social.account` and
`social.post` models, so they cannot live in the same database.

The manifest states it with `"excludes": ["social"]`, so Odoo refuses the
installation with an error when the other module is already installed, and
the other way round. The whole *Social Media* family is affected, since every
module of it depends on this one.

Upgrading from a version before *Social Media Sync* existed.
---------------

Importing the publications, their figures and their comments used to be part
of this module and is now *Social Media Sync*. The move takes a field
(`pending_initial_sync`), two scheduled actions and a controller route from
one module to the other, and it changes what the engagement of an account
means: it is now the average of the daily series instead of the sum of the
publications.

**No migration script is provided**, and none of the modules of the family
carries a `migrations/` directory. They are all on `17.0.1.0.0` and none of
them has been released, so there is no published version to migrate from: the
supported way to pick this up is to recreate the database. Install
*Social Media Sync* alongside the connectors to keep importing.

If a database ever runs a released version of these modules, this note stops
being enough and a migration script becomes required.
