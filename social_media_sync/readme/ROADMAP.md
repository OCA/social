`actor_urn`
---------------

`social.post.account.actor_urn` holds who the social media says published a
publication: the organization page on LinkedIn, the author of the tweet on X.
The import is what fills it, and no view shows it, so nothing reads it back
yet. It looks like it belongs to the reactions, which take the actor
performing them as an argument, and it is the kind of field the family either
starts using or drops.


Storage of the imported medias
---------------

The import downloads the medias of every publication it brings in and stores
them as ordinary `ir.attachment` records, so the filestore grows with the
history of the accounts and not with what is published from Odoo: an account
importing years of publications brings in years of images.

An imported publication has no post to share attachments with, so nothing is
shared here: one image of one publication is one attachment, and the same
image published on two accounts is imported twice. `media_refs` does not
change that, and is not there for it: it is what tells the next
synchronization which references this publication already holds, so that a
media is downloaded once and not on every pass. The bytes of two identical
images still land on the same file, because the filestore keys its files by
the hash of their content; what multiplies is the rows.

What ages them out is one number for the whole database.
`social_media_sync.media_max_age_days` reaches every imported publication
older than it, whatever its account, so there is no way to keep the medias of
one account and age out those of another, and a publication kept only for its
figures still costs its images until that age is reached. The deletion itself
belongs to the vacuum: `_gc_aged_post_medias` releases what the policy
reaches, the next synchronization releases what the social media no longer
serves, and `_gc_lost_media_attachments` deletes both a day later. Serving
those bytes from somewhere else is configured at the level of Odoo, through
`ir_attachment.location`, not from here.
