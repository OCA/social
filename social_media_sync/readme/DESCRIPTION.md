This module brings back into Odoo what an account already published on its
social media: the posts themselves, the figures each of them collected, and
their comments and reactions.

It is separate from *Social Media Base* because of what it costs. Base asks
the social media for a fixed number of things per account — publish, delete,
the daily series of the page — and that number does not change whether the
account published once or ten thousand times. Everything whose cost grows
with the history of the account lives here: one call per page of posts, one
call per publication to check it is still there, one call per comment thread.
An installation that only writes and publishes does not have to pay for any
of it.

*Social Media Base* never names this module. Where base needs something only
the synchronization knows how to do, it declares an empty hook and carries
on, so base works installed alone.

Main features:

- Import of the posts an account already published, and of the statistics
  each of them collected.
- Initial synchronization right after an account is linked, which also fills
  the daily statistics series of the account backwards as far as the social
  media answers. A monthly cron picks up the accounts still waiting for it.
- A weekly full resynchronization, the only pass that notices a post deleted
  on the social media side.
- Verification that a publication still exists remotely, before its thread is
  read.
- Comment thread of a publication, read from the dashboard: a comment is
  written under the account of the publication, a comment is answered where
  the social media serves the replies, and *Recommend* is offered on the
  publication and on each of its comments. Which of them a social media
  really serves is declared by its connector, and only then is the entry
  offered.

This module does not connect to any social media by itself: it brings the
scheduled actions, the frontend and the common interface, and a
synchronization connector is what implements the calls for one social media
in particular.
