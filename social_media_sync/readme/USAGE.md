Importing what an account already published.
---------------

- Right after an account is linked, its publications and their statistics are
  imported: the scheduled action *Social: Initial sync of the new accounts* is
  triggered on the spot and the dashboard shows the account as syncing until
  it is over.
- If that first import fails, the account stops waiting for it and is **not**
  retried on its own: press the *Update* button of the dashboard to import it
  again. The reason is left in the chatter of the account, because the
  scheduled action runs with nobody connected to be notified.
- If the import loses a race against another update of the same account, it
  keeps the account waiting and asks the scheduled action to come back a few
  minutes later. Unlike a web request, a scheduled action gets no retry of its
  own.
- If the social media does not let the import run —the requests of the plan
  are spent, and the account gets a notice saying so— nothing is brought in
  and nothing is recorded as a failure: the account keeps waiting and the
  scheduled action is asked to come back a few minutes later. The *Update*
  button of the dashboard behaves the same way, and only stops announcing the
  first import once the social media was really read.
- Publications created outside of Odoo are the only ones whose medias the
  import has to download, and so the only ones whose images appear on the
  dashboard after it rather than before: a publication sent from Odoo already
  shares the medias of its post.
- The time series of the account is filled backwards when the account is
  linked, by *Social Media Base*, as far back as the social media answers by
  day; the first import only asks for it again when that fill could not be
  read then. How far back that is belongs to the social media, not to Odoo,
  so two accounts may well start with a different depth of history.
- Afterwards, the *Update* button of the dashboard imports again on demand.
  Without this module that button refreshes the daily series of the account
  and the figures of the publications of the last 30 days; with it, the same
  press also imports the publications.
- Pressed with no account picked, the button imports only the accounts known to
  be behind: the ones announcing publications to import and the ones whose
  first import never ran. Pressed on a single account, it imports that account
  whatever it announces. The figures of every account are refreshed either way,
  because they cost a fixed number of calls and they move without anything
  being published; it is the import whose cost grows with the history of the
  account.
- When nothing needed importing, the button says so —*The data was updated. No
  new publications.*— instead of announcing publications it did not bring in.
- The figures imported for a publication — impressions, social media clicks,
  shares, likes, comments, interactions and engagement — are added by this
  module to the list of publications and to their form, which span the whole
  history. The *Statistics* dialog of a card belongs to *Social Media Base*,
  which reads those figures back for the publications of the last 30 days on
  its own; without this module the list and the form show only the tracked
  clicks, counted by the link tracker.
- The totals a post adds up from its publications — likes, comments, clicks,
  shares, interactions and engagement — are drawn by this module on the list
  of posts, and Clicks, Interactions and Engagement on the kanban card of a
  post; without it those columns and that card carry a zero nothing can turn
  into a number.

What each notice on a card announces.
---------------

Three different things can be pending on an account, and each one has its own
notice and its own way out. They are independent: an account may be carrying
one, two or the three of them at once, and none of them says anything about
the others.

- **The credentials expired.** The warning of *Social Media Base*. Only a new
  authorization takes it down, and the *Update* button does not.
- **The first import is running.** Drawn by this module while the scheduled
  action brings in what the account had already published.
- **There are publications to import.** Added by this module when the check for
  updates finds that the account moved on the social media. The *Update* button
  is what resolves it, and the notice goes away on its own once the import is
  over, without the page being reloaded.

Only a social media whose API can tell that an account moved without reading
its publications raises the third one. Where it cannot —reading the timeline
*is* the import— nothing is announced between two runs, and those accounts are
imported on every pass instead.

Noticing what was deleted on the social media.
---------------

- The ordinary import asks the social media only about what it needs, which is
  what keeps it affordable on an account with thousands of publications. What
  it cannot notice that way is that a publication was **deleted** on the social
  media: nothing is left to ask about.
- The scheduled action *Social: Full resync of the accounts* reads everything
  again once a week and reconciles it, and each connector may also offer to run
  it on demand from the account form. A publication deleted on the social media
  may therefore take up to a week to be reported as such.
- A publication found gone is marked as *Deleted* and keeps its reference on
  the social media: detection is not infallible, so a line wrongly marked can
  be recognised and restored by the next full pass.
- Opening a publication already asks the social media without this module, so
  a deletion the user runs into is marked right away either way. What this
  module adds is noticing the ones nobody opens.

Comments and reactions.
---------------

- Commenting a publication from the dashboard publishes the comment on the
  social media, under the account of the publication, which is what the
  composer announces.
- Answering a comment moves the composer under it, so the reply is written
  where it will be read. Once the reply is published the composer returns to
  the head of the dialog; only a reply the social media rejected keeps the
  aim, so the retry starts under the same comment. Pressing the entry again
  hands the composer back to the head of the dialog, which also holds it
  while the answered comment is not on the list.
- A comment is answered where the social media serves the replies. Where the
  whole thread already arrives with the comments, the replies are nested from
  what is already on screen and nothing else is asked for.
- *Recommend* is offered both on the publication and on each of its comments,
  and is sent under the same account. It is only shown where the social media
  supports it on comments: a connector that recommends them declares itself,
  and the entry is not rendered for the publications of the ones that do not.
- The entry is a toggle: a social media holds one reaction per account, so it
  draws what the account already recommended and pressing it there withdraws
  the reaction. A social media that could not be read leaves the entry as it
  was drawn instead of claiming one thing or the other.
- A reaction or a comment that fails with a *not found* does not mark the
  publication as deleted on its own: the publication is asked about first,
  because a social media answers the same for a reference it does not
  recognise and for a lost permission.
