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

Publishing options are not configurable
---------------------------------------

- The visibility, the feed distribution, the targeting by country, language or
  industry and the third party distribution are fixed in the code, so a
  publication cannot be restricted nor targeted from Odoo. Offering them means
  exposing them on the post and validating the combinations LinkedIn accepts.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

Size and duration of a video are not checked
--------------------------------------------

- Odoo does not check them before uploading: those limits are the ones of the
  [Videos API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api)
  and LinkedIn applies them while processing. A video out of limits is
  transferred whole and rejected afterwards, in the processing phase, with
  *LinkedIn could not process the video*.

Rate limits are not handled
---------------------------

- The module does not handle the
  [throttle limits](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)
  of LinkedIn, applied per day and per application. When LinkedIn answers with
  a limit error, the operation is recorded as failed like any other error and
  has to be retried later by hand; only a credential rejection triggers an
  automatic retry, and only once.

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
  requested by this module.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/organization-social-action-notifications

Reactions other than Like
-------------------------

- Only `LIKE` is sent, both on a publication and on a comment. The
  [Reactions API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/reactions-api)
  also takes `PRAISE`, `EMPATHY`, `INTEREST`, `APPRECIATION` and
  `ENTERTAINMENT`, and it deletes a reaction as well, which is not offered
  from Odoo either. Nothing on the LinkedIn side holds them back — the same
  endpoint and the same permissions serve them — so offering them is a matter
  of choosing the reaction on the dashboard and of deciding what withdrawing
  one means for the figures already imported.

Video of a publication
----------------------

- The video of a published post is not attached to the publication imported
  from LinkedIn: only the *has video* flag is kept. Bringing the file over
  means downloading it from LinkedIn on every synchronization, which is not
  implemented.
