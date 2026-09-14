Nothing has to be configured for this module: it reads X with the credentials
the account already holds, which are configured in *Social Media X*.

What those credentials need is an App able to spend against the API, the same
one the connector requires: the timeline of the user and the recent search
this module spends are X API v2 endpoints, so a developer App outside a
Project answers ``403`` to them as it does to the rest. See the configuration
of *Social Media X* and
[the pricing of the X API](https://docs.x.com/x-api/getting-started/pricing).

This module is where the pay-per-use bill of an X account is decided. Reading
a publication of the account costs $0.001, but the replies the comments
dialog reads are posts of other people, at $0.005 each, and it asks for up to
five pages of a hundred while it stays open, refreshing itself every two
minutes. The 24-hour deduplication of X charges the same reply once however
many times it is read, so what is paid is the replies that are new, not the
dialog being open; even so, a busy thread is the most expensive thing the
modules do against X. The *Enable since* date below is the lever: nothing
before it is ever read.

Enable since
------------------------
- Go to *Social Media* > Configuration > Accounts
- Select the account
- Select *Enable since*
- The *Post since* field is then enabled, allowing you to select the post to
  start the search for in the next post retrieval. The import no longer
  reads what is older than that publication, but the figures of the
  publications of the last 30 days are read back all the same by *Social
  Media X*; older than that, each publication keeps the last figures that
  were read for it.

  ![ENABLE_SINCE](../static/img/readme/ENABLE_SINCE.png)

Scheduled actions
------------------------

The passes over an X account are the ones *Social Media Sync* declares, plus
two of *Social Media Base*: the check for updates and the daily refresh of
the figures of the recent publications.

- *Social: Checking social media updates*, every 2 hours, reads the timeline
  of every X account. X has no cheap answer to whether anything moved — the
  only endpoint that knows is the timeline, and reading it is already the
  import — so this pass imports instead of flagging the account.
- *Initial sync of the new accounts*, monthly, imports the timeline of an
  account that was just linked. Linking one triggers this action immediately
  as well, so its card is filled from the first moment.
- *Full resync*, weekly, reads the timeline of an X account exactly as the
  ordinary import does, so it notices nothing that was deleted there. A
  publication deleted on X is marked *Deleted* when someone opens it from the
  dashboard or from its form, which is a check of *Social Media X*.
- *Social: Refresh the statistics of the recent publications*, daily, reads
  the publications of the last 30 days by identifier, which is a call of
  *Social Media X* and not of this module.

An account whose first import has not run yet is left out of the bihourly
check, because that check and the initial import write the same row from two
threads.
