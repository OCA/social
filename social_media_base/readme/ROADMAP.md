Multi-company scope of the posts.
---------------

The accounts (`social.account`) and their daily statistics
(`social.account.statistics`) are the multi-company records: they carry a
company and a record rule that filters them. The posts and their publications
have neither a company field nor an equivalent rule, so they are only filtered
by their responsible user. In a multi-company database a social media
administrator therefore sees the posts of every company.


Figures older than the window
---------------

The daily refresh reads back the publications of the last 30 days, which is
what keeps its cost independent of the history of the account. A publication
that was already older than that when the module was installed therefore stays
at zero for good: nothing brings it inside the window again. It is accurate —
nobody ever asked the social media about it — but on a card it reads like a
figure that failed to arrive, and there is no way from here to tell the two
apart. Reading the history of an account is what *Social Media Sync* is for.

The figures of those views are added by that module for the same reason: the
list, the search filters and the form of a publication span the whole history,
where a figure inside the window sits next to one that was never read. The
*Statistics* dialog of a card does not, and it draws them all.


Storage of the medias of a post
---------------

The images and videos of a post and of its publications are ordinary
`ir.attachment` records, kept for as long as the record that owns them. A post
published on several accounts stores each media once, because every
publication points at the attachments of the post instead of copying them, and
what each social media made of that media is a reference in `media_refs`.

What ages a media out lives in *Social Media Sync*, which is where the cost
grows with the history of an account: it downloads a media of its own for
every publication it imports, and a maximum age in days releases them. The
medias of a post are out of that reach on purpose, being editorial content
that a post stores once however many accounts it went to.

Inside this module the deletions are the cascade that takes the medias of a
post or of a publication when the record itself is deleted, the vacuum that
deletes a day later the medias a post let go of, and
`social.account.action_purge_account`, which drops an account with its
publication history. Moving those bytes out of the filestore is not something
this module decides either: an external backend is configured at the level of
Odoo, through `ir_attachment.location`, and applies to every attachment of the
database.
