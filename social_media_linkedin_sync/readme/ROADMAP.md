One definition per symbol
-------------------------

The calls of this module cross towards *Social Media Linkedin*, never the
other way around: `_request_linkedin`, `_get_posts`,
`_linkedin_statistics_values`, `_get_linkedin_daily_statistics`,
`_refresh_post_statistics` with the reading by URN behind it —
`_get_entity_statistics`, `_get_entity_share_statistics`,
`_get_ugc_posts_statistics`, `_parse_share_statistics`, `_filter_urns` — and the
constants of `social_linkedin_utils.py` are asked for where the connector
defines them. The import does not read the figures of a publication either: it
hands the page it discovered, plus the publications the page did not bring, to
`_refresh_post_statistics` and lets the connector spend the calls. Copying one of them here would be the failure that shows in
nothing: the two copies drift apart with the first change, and the daily
series and the import mark stop speaking the same language.

Where the connector needs something only this module knows how to do, it
declares an empty hook — `_linkedin_check_updates` — and this module
overrides it.

Where the daily series is filled
---------------------------------

`_backfill_statistics` is the empty hook of *Social Media Base* and *Social
Media Linkedin* implements it, so neither the method nor the calls it spends
belong to this module. Base asks for it the moment an account is associated,
the *Rebuild statistics history* button of the account form asks for it
again with `force=True`, and the initial synchronization of *Social Media
Sync* asks for it once more, which on an account that already holds its
series is the retry of an association whose history could not be read
rather than a repetition of it.

They are the figures of the whole page --what the finder answers without a
list of URNs counts what was published before Odoo and outside of it-- so
what this module changes is when the series is asked for again, not what is
being counted.

`_snapshot_statistics`, `_linkedin_backfill_window` and
`_STATISTICS_HISTORY_MONTHS_LINKEDIN` stay in the connector, and so do the
calls that use them: `_backfill_statistics` is the only caller of the three.
This module asks for none of them.

Who wrote a comment
-------------------

- **A person cannot be named.** `GET /v2/socialActions/{urn}/comments`
  identifies the author of a comment by a URN and nothing else, and no public
  endpoint turns a `urn:li:person:` into a name: the
  [Profile API](https://learn.microsoft.com/en-us/linkedin/shared/integrations/people/profile-api)
  answers for the authenticated member alone, `r_1st_connections_profile` was
  retired, and the token the connector holds belongs to the page and not to a
  person. The website shows the name because it reads endpoints of its own
  that are not exposed. Reading it needs the Partner Program, an access level
  of the application.
- What the module does with that limit is resolve what can be resolved and
  say nothing where it cannot. The account itself is named from Odoo, an
  organization is read with `GET /v2/organizations/{id}`, and everything else
  is drawn as *LinkedIn member* or *LinkedIn page*. A comment is never signed
  with the name of the page that did not write it.
- An organization the account does not administer may answer `403`. The
  thread keeps loading, that comment falls back to the neutral label and the
  refusal is only logged: a name is not worth a thread.
- The names are resolved once per thread and not kept. A cache of actors
  would save the calls a reopened dialog repeats, and it would need its own
  expiry and its own security; it is not implemented.

Media in the comments
---------------------

- A comment is published with its text alone: the connector sends `actor`,
  `message` and `object`, never `content`, and the comment composer offers no
  attachment for a LinkedIn publication.
- The [Comments API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api)
  documents an example carrying media, and it is not what an ordinary
  application gets. Measured against a real page on 2026-08-24, with an image
  already uploaded through the Images API, the two ways of sending it answer:
  - `POST /rest/socialActions/{urn}/comments` — `403 ACCESS_DENIED`,
    *"Not enough permissions to access: partnerApiSocialActions.CREATE"*. The
    versioned resource belongs to the Partner Program, which is an access
    level of the application and not something a paid plan buys.
  - `POST /v2/socialActions/{urn}/comments`, the endpoint the connector talks
    to, with the same payload plus `content` — `500 Internal Server Error`,
    while the very same call without `content` publishes the comment.
- So the media stays out until LinkedIn grants that access to the
  application: the endpoint that would take it is refused, and the one that
  answers does not accept the field.


The weekly full resync is not spread over the days
--------------------------------------------------

- The *Full resync* button reconciles **one account**, the one it is pressed
  on. The scheduled action does not: it walks every account of the database in
  the same weekly run, each in its own savepoint, and that is the expensive
  pass, one call per hundred publications of each account.
- On a database with several large pages that single run could exhaust the
  daily quota and make the manual refresh fail with it. Spreading the accounts
  over the days of the week is the way out and is not implemented.


Asking LinkedIn only for what changed
-------------------------------------

- **It is not possible with these endpoints**, so the statistics cost one call
  per batch of identifiers whatever moved:
    - The `/posts` finder takes `author`, `start`, `count`, `sortBy` and
      `viewContext`. There is no `since` of any kind, so there is no equivalent
      to what the X connector does with `since_id`.
    - The statistics of specific publications cannot be restricted to a period:
      *"Time-bound statistics is not supported for specific share queries"*.
    - The daily figures of the page say that something moved, not which
      publication moved.
- There **is** a stream of engagement events, and it is not used. It would tell
  which publication changed, and with it the refresh could ask about that one
  alone. It is not implemented because of three limits worth weighing first:
  it only reports reactions, comments and reshares, never impressions or
  clicks, which would still need the ordinary refresh; the publication it
  points at comes as an `urn:li:activity:` and only the webhook payload carries
  the matching `urn:li:share:`, the pull finder does not, so pulling alone
  cannot attribute an event to a publication; and the webhook needs a publicly
  reachable HTTPS URL validated by LinkedIn plus a subscription per member and
  organization. The permission it needs, `rw_organization_admin`, is already
  requested by *Social Media Linkedin*.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/organization-social-action-notifications


Reactions other than Like
-------------------------

- Only `LIKE` is sent, both on a publication and on a comment. The
  [Reactions API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/reactions-api)
  also takes `PRAISE`, `EMPATHY`, `INTEREST`, `APPRECIATION` and
  `ENTERTAINMENT`. Nothing on the LinkedIn side holds them back — the same
  endpoint and the same permissions serve them — so offering them is a matter
  of choosing the reaction on the dashboard, and of drawing an entry that is
  no longer one thumb with two states.


Video of a publication
----------------------

- The video of a published post is not attached to the publication imported
  from LinkedIn: only the *has video* flag is kept. Bringing the file over
  means downloading it from LinkedIn on every synchronization, which is not
  implemented.
