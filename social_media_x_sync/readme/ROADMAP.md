- Only the hundred latest likes of the account are read, in a single page,
  so a publication or a comment the account liked before them is drawn as not
  recommended. Pressing *Recommend* there does no harm — X answers that the
  like is already given, and the entry is drawn right — but reading further
  back costs one page per hundred likes, every post of it charged, and grows
  with the history of the account.

- *Delete* is offered on the comments of the account that answer the
  publication, not on its replies inside a thread: *Social Media Sync* hides
  the entry on every reply, whatever the social media. Offering it there is a
  change in *Social Media Sync*; until then, a reply of the account is deleted
  on X itself.

- The card of an imported publication does not play its video: it counts
  the videos, and the file is played in the form of the publication.

- The video or the animated GIF of a comment is not played in Odoo. The
  dialog of the comments shows its cover as one more image of the comment,
  and the video itself is watched on X.

- Only the mp4 files X lists for a video are downloaded. The HLS playlist
  (`application/x-mpegURL`) X lists next to them is not used, because Odoo
  cannot play it without a player of its own.

- The timeline is read once and `next_token` is never followed, so an account
  with more than 100 publications is only imported up to that page. Paginating
  it costs one request per page against the plan of the account.

- The conversation of a publication is read up to 5 pages of 100 replies, so a
  thread longer than 500 replies is read truncated; what is missing is said
  instead of guessed, because no comment of a truncated read states how many
  replies it has. Raising the ceiling costs one request per page against the
  plan of the account, and it is paid again on every refresh: the dialog of the
  comments rereads the conversation whole every two minutes while it stays
  open. Reading only the first page on those refreshes, and the whole
  conversation only when the dialog opens, is what would make a higher ceiling
  affordable.
