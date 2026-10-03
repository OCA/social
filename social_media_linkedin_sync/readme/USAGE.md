Importing what a page already published.
----------------------------------------

- The *Update* button of the dashboard imports the publications of the
  pages. Without this module that button refreshes the daily series of the page
  and the figures of the publications of the last 30 days; with it, it also
  brings in the publications Odoo does not have yet and the figures of the ones
  older than that window.
- The import discovers the publications three ways: one publication by its
  reference, the whole feed page by page, or — the ordinary path — the first
  page of the feed sorted by last modification, which is what catches what
  changed since the previous pass.
- It also downloads the medias of the publications created outside of Odoo, so
  those images appear on the dashboard only after the import.
- The publication mirrors what is online: an image removed from the post on
  LinkedIn is dropped from the dashboard card on the next import. Only the
  medias downloaded from LinkedIn are managed this way, so a file attached by
  hand in Odoo is never removed.
- An import of the whole page leaves a mark with the figures of the last
  watched days. The bihourly check compares against that mark, which is why
  importing is what takes the notice down; refreshing a single publication
  takes it down too but leaves the mark alone, since one publication says
  nothing about the rest of the page.
- The first import asks for the time series again on an account whose
  association could not read it, which is the retry of a backfill that
  failed and not a repetition of it. How far back the series goes is the
  connector's business: *Social Media Linkedin* fills it as far back as
  LinkedIn answers by day the moment the account is linked, and rebuilds it
  from the *Rebuild statistics history* button of the account form.

Comments and reactions.
-----------------------

- The comment thread of a publication is read from the dashboard, and its
  replies with it: LinkedIn serves the replies of a comment apart, so they are
  asked for when the thread is opened.
- A comment and a reply are written under the organization, and the thread
  offers to delete a comment: LinkedIn is the one deciding whether the
  organization may, and its refusal is reported instead of removing it here.
- *Recommend* is offered on the publication and on each of its comments, sent
  under the organization. LinkedIn holds one reaction per account and only
  `LIKE` is sent, so the entry is a toggle: it shows a filled thumb on what
  the organization already recommended, and pressing it there withdraws the
  reaction. What LinkedIn holds is read back on every import, so a reaction
  made or withdrawn from LinkedIn itself reaches the dashboard on the next
  pass.
- LinkedIn does not accept an image in a comment, so the composer offers no
  upload on a LinkedIn thread.

Publications deleted on LinkedIn.
---------------------------------

- Posts deleted directly on LinkedIn are marked as *Deleted on LinkedIn* in
  Odoo, so the dashboard keeps their history. Only the *Full resync* button
  and the weekly scheduled action notice them, not the ordinary import, so a
  deletion can take up to a week to be reported.
- Opening a publication asks LinkedIn first, so one deleted there is reported
  and marked right away instead of waiting for the weekly pass.

Full resync of a page
---------------

- Go to *Social Media* > Configuration > Accounts, select the account and click
  on the *Full resync* button of the header.
- The *Update* button of the dashboard reads one page of the feed, the one
  sorted by last modification, and refreshes the figures of every publication
  by its identifier. That is enough for everything except one thing: it cannot
  notice that a publication was **deleted** on LinkedIn, because a publication
  missing from the page it read is not necessarily gone.
- *Full resync* is what reads the whole feed and marks as *Deleted on LinkedIn*
  what is no longer there. It is also the expensive pass, one call per hundred
  publications against the daily quota, so it asks for confirmation.
- The scheduled action *Social: Full resync of the accounts* does the same
  weekly for every account, so pressing the button is only needed to see a
  deletion reported sooner.
- A publication edited on LinkedIn long enough ago to have fallen off that
  first page keeps the text Odoo already had until a full resync. Its figures
  are refreshed all the same.

How the synchronization spends the LinkedIn quota
---------------

The [throttle limits](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)
of LinkedIn are counted per day, per application and **per endpoint**, so
what matters is not the total number of calls but how they spread.

- The scheduled action checking for updates costs **two calls per account and
  run**, whatever the number of publications, one when it does find something,
  and only one for an account already announcing publications to import or for
  one whose credentials expired: the daily series of the page is written for
  them all the same, and what is skipped is the second call, the peek at the
  feed that could only confirm what the dashboard already says or fail on a
  token known to be dead. No call at all is spent on an account with no
  organization linked, since the finder is addressed by organization and
  there is nothing to ask. It reads the figures LinkedIn reports for the whole page
  day by day and compares them against the ones the last import left: no
  publication is read one by one to decide whether the dashboard should
  announce updates. Running every two hours, that is around 24 calls a day per
  account.
- The **Update** button does not walk the feed. The statistics are asked for
  by publication identifier, and those identifiers are already stored in Odoo,
  so one page of the feed is enough: the one sorted by last modification, which
  is what brings the publications created or edited on LinkedIn. That is one
  call instead of one per hundred publications.
- The figures of the publications are not read here: the import hands the
  identifiers to *Social Media Linkedin*, which is where that reading lives, so
  the same three calls answer the page whether they are asked for by this
  import or by the daily refresh of the connector.
- Those figures are asked in as many calls as the 4 KB limit of the query
  string needs, since those endpoints take every identifier in the URL and none
  of them paginates. Around a hundred publications fit in one call, so a full
  feed takes several.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/share-statistics

- *Full resync* is the expensive pass, one call per hundred publications. The
  button does it for the account it is pressed on; the weekly scheduled action
  does it for every account of the database. It walks the feed page by page (`count=100`) up to as many pages as
  `social_media_linkedin_sync.posts_max_pages` allows, **fifty by default**,
  that is 5000 publications, and a page is only taken as the last one
  when it comes back empty, because LinkedIn documents that a page may carry
  fewer publications than asked while more are left. On an account whose feed
  is longer than that, the answer is incomplete and the sweep that marks as
  *Deleted* what is no longer on LinkedIn is skipped for that run: reporting
  nothing is preferable to marking a publication that is still online.

What the check for updates does and does not notice
---------------

- It only tells that *something* on the page moved, not which publication
  moved. It does not need to: the only thing it decides is whether the
  dashboard shows the notice inviting to synchronize. A change that cancels
  itself out between two runs, a reaction removed and another one added,
  leaves the figures of the page where they were and goes unnoticed until the
  next synchronization.
- It watches the **daily** figures of the page, over a window of the last
  seven days, and not the lifetime totals the same endpoint answers when no
  time interval is given. The two are two separate reads of LinkedIn's own
  data, so they are not guaranteed to agree at every instant; this module
  only relies on the daily buckets. One consequence worth knowing: activity
  older than the seven-day window is not announced.
  It is imported all the same when the user synchronizes, because the import
  reads the publications themselves and not this window.
- The engagement is not compared. It is a ratio of the clicks, reactions,
  comments and shares over the impressions, so it cannot move without one of
  those moving, and it is the only non-integer figure of the set.
- The statistics endpoint only answers activity of the **last 12 months**, on a
  rolling window. A publication older than that stops being counted, which can
  move the figures of the page on its own, with nobody having interacted with
  anything. The check announces updates once when that happens and the next
  import reconciles it.
