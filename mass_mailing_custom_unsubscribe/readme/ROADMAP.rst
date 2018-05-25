* As version 11 has introduced a new relation type between mailing lists and
  contacts that has multiple usability issues that are being reworked by Odoo
  to land in version 12, this module falls back to the version 10 behaviour in
  which one contact belonged to just one list.
* This module replaces AJAX submission core implementation from the mailing
  list management form, because it is impossible to extend it. When
  https://github.com/odoo/odoo/pull/14386 gets merged (which upstreams most
  needed changes), this addon will need a refactoring (mostly removing
  duplicated functionality and depending on it instead of replacing it). In the
  mean time, there is a little chance that this introduces some
  incompatibilities with other addons that depend on ``website_mass_mailing``.
