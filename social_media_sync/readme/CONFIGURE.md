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
and the files are deleted a day later. One run reaches a thousand
publications and takes them in the order they were created, so a database
holding more aged publications than that keeps the medias of the ones beyond
the first thousand. Two things to weigh before writing a number:

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
