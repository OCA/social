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
- The import also downloads the medias of the publications created outside of
  Odoo, so those images appear on the dashboard only after it.
- The first import fills the time series of the account backwards, as far back
  as the social media answers by day. How far that is belongs to the social
  media, not to Odoo, so two accounts may well start with a different depth of
  history.
- Afterwards, the *Update* button of the dashboard imports again on demand.
  Without this module that button only refreshes the daily series; with it, it
  does both.

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
- Opening a publication, from its form or from its card on the dashboard, asks
  the social media first. A publication deleted there is reported as *The post
  does not exist or has been deleted.* and marked right away, instead of
  waiting for the weekly pass. A check that fails to reach the social media
  answers *not deleted*: a publication is not gone just because Odoo could not
  read it.

Comments and reactions.
---------------

- Commenting a publication from the dashboard publishes the comment on the
  social media, under the account of the publication, which is what the
  composer announces.
- A comment is answered where the social media serves the replies. Where the
  whole thread already arrives with the comments, the replies are nested from
  what is already on screen and nothing else is asked for.
- *Recommend* is offered both on the publication and on each of its comments,
  and is sent under the same account. It is only shown where the social media
  supports it on comments: a connector that recommends them declares itself,
  and the entry is not rendered for the publications of the ones that do not.
- A reaction or a comment that fails with a *not found* does not mark the
  publication as deleted on its own: the publication is asked about first,
  because a social media answers the same for a reference it does not
  recognise and for a lost permission.
