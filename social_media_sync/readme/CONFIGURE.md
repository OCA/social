Nothing has to be configured for this module to work: it uses the accounts,
the credentials and the groups of *Social Media Base*.

What is worth reviewing is the two scheduled actions it adds, in
*Settings / Technical / Automation / Scheduled Actions*:

- *Social: Initial sync of the new accounts* runs monthly, and is also
  triggered on the spot every time an account is linked. It only picks up the
  accounts still waiting for that first import, so the monthly run is a safety
  net rather than the normal path.
- *Social: Full resync of the accounts* runs weekly. It is the only pass that
  notices a publication deleted on the social media, and the most expensive
  one: it reads every publication of every account, one call per page. Making
  it run more often is what turns a deletion noticed a few days late into a
  quota problem.

Both intervals are the ones to move if the social media of an account is
strict about quotas.

The retention of the downloaded medias is one system parameter, in *Settings /
Technical / Parameters / System Parameters*, which only an administrator
reaches: `social_media_sync.media_max_age_days`. The module installs it at
`0`, so it is there to be found, and zero is no policy at all: no media is
ever released.

A system parameter holds text, and this one is read as a number of days. A
value that cannot be read as one — a word — is taken as no policy and leaves
a warning in the log; an empty value, zero and any negative number are no
policy too and are not worth a warning. No media is released in any of those
cases.

Written as a positive number of days, the daily vacuum releases the images and
videos this module downloaded for the imported publications older than that,
and the files are deleted a day later. One run reaches a thousand of the
aged publications that still hold medias. A publication already released
leaves the next run instead of taking the place of another one, so a database
holding more aged publications than that is released in full over the
following runs. Two things to weigh before writing a number:

- *What is lost* is the media itself. The card of an aged publication is drawn
  with no image and no placeholder in its place. The link to the social media,
  where the media still is, stays.
- *What is kept* is what each social media made of that media. The next
  synchronization pass knows the publication already had it and does not ask
  for it again, so the policy frees the disk once instead of paying for the
  same bytes every week.

Only the publications imported from a social media are reached. The medias of
a post published from Odoo are editorial content and are never aged out,
whatever the age of the post.

The size of each downloaded media is capped by a second system parameter, in
the same place: `social_media_sync.media_max_size_mb`. The module installs it
at `100`, in megabytes, and an update of the module does not overwrite what an
administrator wrote in it. A media is held whole in memory while the import
runs, and the cap is what keeps one large video from exhausting it.

A media larger than the cap is not downloaded. When the social media announces
the size of the file, the download stops before reading it; when it does not,
it stops as soon as what was read goes past the cap. The publication is
imported without that media, and a warning in the log names the media, its
size and this parameter. As the publication does not hold that media, every
synchronization pass asks for it again and stops at the cap again, until the
parameter is raised above its size. A long video can well be larger than
`100` megabytes, so an account publishing them is the one to raise it for.

Zero is no cap at all, and so are an empty value, any negative number and a
parameter that was deleted:
every media is downloaded whatever its size, and nothing is logged. A value
that cannot be read as a whole number of megabytes — a word, a decimal — does
not remove the cap: it is taken as `100` and leaves a warning in the log.
