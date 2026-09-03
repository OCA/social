Tracked links.
---------------

- The short links published on the social media point at this Odoo, so
  **`web.base.url` has to be the address the social media audience can
  reach**. Set it in *Settings / Technical / System Parameters*, and add
  `web.base.url.freeze` set to `True`, otherwise every administrator login
  rewrites it with the host that was used.
- The parameter `link_tracker.no_external_tracking` must stay unset: with it
  the UTM parameters are stripped from the links pointing outside this Odoo.
- The *Social Media / User: Own Accounts* group is granted write access on
  `link.tracker`, which the core module only grants for reading. A user
  without it cannot publish a post containing a link.
- Each social media reports a *UTM Medium*, taken from the `social.media`
  record. The connector modules provide a default one, and it can be
  overridden per social media.
