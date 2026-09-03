This module provides the fundamental foundation for social media management.
It facilitates the integration of user accounts, posts and native graph and
pivot analysis over a daily time series. Designed to be flexible and scalable,
it allows developers and businesses to integrate and customize social features
according to their needs.

What it asks of a social media is always a fixed number of calls per account:
publishing, deleting, and the daily series of the page. Reading back what an
account already published — the publications themselves, their figures, their
comments — costs one call per page or per publication, so it grows with the
history of the account and lives in *Social Media Sync* instead. Without that
module the dashboard still works: the figures of a card are added up from what
is already stored, and the counters of a publication stay at zero because
nobody ever asked the social media about it.

This module does not connect to any social media by itself: it brings the
models, the security, the scheduled actions and the common interface. To use
it, a connector module has to be installed as well (for instance
*Social Media Linkedin* or *Social Media X*), which is what registers the
social media, implements the OAuth authorization and publishes for real.

Main features:

- Integration of multiple user accounts.
- Basic methods that can be extended and adapted to suit the social media.
- Basic business structure.
- Dashboard of published posts with video and deletion indicators.
- A *Campaigns* menu inside the application, so the Odoo marketing campaigns
  (`utm.campaign`) can be managed without installing another marketing
  application. A post carries the campaign it belongs to, and the campaign
  form opens a new post already attached to it.
- Campaign badge on the posts kanban and on the dashboard cards.
- The posts of a marketing campaign, shown on the campaign from the moment
  they are drafted, with their consolidated figures and a stat button on the
  campaign form, the same way *Email Marketing* and *SMS Marketing* plug into
  a campaign.
- A UTM medium per social media and a UTM source per publication, so the
  links of a post are tracked separately for each account it is published on.
- Links of a published message routed through the Odoo link tracker, so a
  click from the social media is counted in Odoo and attributed to the
  campaign and to the publication.
- Because of the above the module depends on `utm` and on `link_tracker`,
  which are installed with it. They are core modules that bring the marketing
  campaigns, the mediums, the sources and the short links, and they change
  nothing in the social media data.
- Statistics stored as one row per account and day, so a native graph and a
  pivot draw them with the search panel, the comparison and the export of
  Odoo. Only the social media reporting figures by day fill it. A cron
  rewrites the last days every two hours, because the social media revise
  figures already past, and the *Update* button of the dashboard rewrites the
  same window on demand.
- Figures of the dashboard card added up from what is already stored, so
  opening the dashboard costs no call at all, however many publications the
  account has.
- Account credentials (OAuth tokens) are only visible to administrator users.
- What each social media refuses to publish, shown on the post while it is
  written instead of when it is sent. Every connector declares its own rules
  once — how long the message may be, how many images and videos, which
  formats and which sizes — and the post form shows two blocks: what a social
  media will publish differently from what is written, and what it will not
  publish at all. Saving is never blocked, because a post is written before it
  is finished; the publication is where an objection stops something, and it
  reads the very same rules, so the form and the publication can never
  disagree. A publication refused this way fails on its own line: the other
  accounts of the post go out as usual.
