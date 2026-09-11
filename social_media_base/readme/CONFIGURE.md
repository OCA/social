Tracked links
-------------

- The short links published on the social media point at this Odoo, so
  **`web.base.url` has to be the address the social media audience can
  reach**. Set it in *Settings > Technical > Parameters > System Parameters*,
  and add `web.base.url.freeze` set to `True`, otherwise every administrator
  login rewrites it with the host that was used.
- The parameter `link_tracker.no_external_tracking` must stay unset: with it
  the UTM parameters are stripped from the links pointing outside this Odoo.
- The *Social Media / User: Own Accounts* group is granted write access on
  `link.tracker`, which the core module only grants for reading. A user
  without it cannot publish a post containing a link.
- Each social media reports a *UTM Medium*, taken from the `utm_medium_id`
  field of its `social.media` record. *Social Media Linkedin* answers the
  LinkedIn medium of `utm`, and a social media that answers none reports the
  *Social Media* medium this module ships. No view draws the field, so a
  medium of its own is written from a data file.
