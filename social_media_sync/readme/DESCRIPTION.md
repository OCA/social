This module brings back into Odoo what an account already published on its
social media: the posts themselves, the figures each of them collected, and
their comments and reactions.

It is separate from *Social Media Base* because of what it costs. Base asks
the social media for a fixed number of things per account — publish, delete,
the daily series of the page, the figures of the publications of the last 30
days — and that number does not change whether the account published once or
ten thousand times. Everything whose cost grows with the history of the account
lives here: one call per page of posts, one call per publication to check it is
still there, one call per comment thread. An installation that only writes and
publishes does not have to pay for any of it.

*Social Media Base* never depends on this module nor calls into it. Where
base needs something only the synchronization knows how to do, it declares
an empty hook and carries on, so base works installed alone.

Main features:

- Import of the posts an account already published, and of the figures each of
  them collected however old it is. Base reads back the publications of the
  last 30 days on its own and draws them in the *Statistics* dialog; what this
  module adds are the views that span the whole history — the list of
  publications, its search filters and the ordinary form — and the likes and
  the comments the footer of a dashboard card draws for the social media whose
  connector reports them. A publication older than that window only carries
  figures once this import has run.
- Initial synchronization right after an account is linked, which imports
  what the account already published. A monthly cron picks up the accounts
  still waiting for it, and that same pass asks for the daily statistics
  series again for an account whose history could not be read when *Social
  Media Base* filled it at association.
- A weekly full resynchronization, the only pass that notices a post deleted
  on the social media side.
- Verification that a publication still exists remotely, for the ones nobody
  opens: the weekly pass asks the social media about them, and a reaction or
  a comment answered with a *not found* has the publication itself asked
  about before the line is marked. Asking about the one publication a user
  opens is *Social Media Base*'s and costs the same call with or without this
  module.
- Comment thread of a publication, read from the dashboard: a comment is
  written under the account of the publication, a comment is answered where
  the social media serves the replies, a comment of the thread is deleted
  after a confirmation, and *Recommend* toggles the reaction of the account on
  the publication and on each of its comments. Which of them a social media
  really serves is declared by its connector, and only then is the entry
  offered.

This module implements the API of no social media in particular: it brings
the scheduled actions, the frontend and the common interface, and a
synchronization connector is what implements the calls for one social media.
The only thing it fetches on its own is the media of an imported publication,
from the URL the connector hands it.
