Importing the publications
------------------------

- The timeline of the account is read with
  [the posts of a user](https://docs.x.com/x-api/posts/user-posts-timeline),
  which answers up to **100 publications in a single request** and is not
  paginated: what is older than those hundred is not imported, in order to
  spare the requests of the plan. Retweets and replies are excluded, so only
  the original publications of the account are stored.
- Each media X answers with a direct address is downloaded once and stored as
  an attachment; one it answers without a direct address is not stored. A
  media already stored is not asked for again.
- The *Update* button of the dashboard runs the same import on demand, over
  every account shown.
- The module adds the *With Reposts* and *With Quotes* filters to the search
  panel of the dashboard, next to the filters of impressions and interactions
  of *Social Media Sync*.
- With *Enable since* the import only asks for what was published after the
  stored publication, so the older publications are no longer read by this
  import. The ones published in the last 30 days are refreshed all the same by
  *Social Media X*, which reads their figures by identifier. The card of the
  account is unaffected either way: the figures are written on each
  publication, and the card adds up every publication stored.

Comments
------------------------

- A comment or a reply written on an X thread may carry images. The composer
  offers the upload, the files travel to X with the reply and are shown on
  the published comment.
- The comments of a publication are read with the
  [recent search](https://docs.x.com/x-api/posts/recent-search) endpoint of X,
  which only covers the **last 7 days**: the replies to older publications are
  not shown on the dashboard even though the post has them. Retweets and
  quotes are excluded as well, only the replies are listed.
- The conversation is read a hundred replies at a time, following the token X
  answers with until it runs out or five pages have been read. Read to the
  end, how many replies each comment has is counted in Odoo and never asked to
  X again; cut short by that ceiling or by the limit of requests of the plan,
  no number is stated, and the dashboard offers to unfold the replies of every
  comment.
- Answering a publication and answering one of its comments are the same call
  to X: on X a comment is a post like any other, and what changes is the post
  being replied to.

What this module does not detect
------------------------

- Its own passes do not detect a publication deleted on X: a publication
  deleted there is marked *Deleted* only by the check *Social Media X* makes
  when the publication is opened.

Rate limits
------------------------

The endpoints this module spends from the plan of the account are the timeline
of the user, the recent search of the comments and the publication of a
reply. Each of them has its own window on the account, the same record where
*Social Media X* stores the windows of the endpoints it spends —the read of a
single post and the read of the figures by identifier—, and when X answers
that one is exhausted Odoo stops calling that endpoint until the window
expires.

While the window of the comments lasts, opening the conversation of a
publication shows the notice *The comments could not be read from X. The
account may have reached the limit of requests of its plan.* instead of an
empty thread, and a refresh in that state leaves the comments already on
screen untouched.

While the window of the replies lasts, publishing a comment answers *The
comment could not be published on X. The account may have reached the limit
of requests of its plan.* instead of reporting a reply X never received. The
text of the composer is not kept, but the comment being answered stays aimed
at, so the retry starts under the same comment.

Uninstalling
------------------------

Uninstalling this module leaves the account linked and able to publish. What
goes with it is the checkpoint of the import: *Enable since*, *Post since* and
the reference of the last publication read.
