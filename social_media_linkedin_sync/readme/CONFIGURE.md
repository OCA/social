Nothing has to be configured for this module to work: it uses the LinkedIn
accounts and credentials of *Social Media Linkedin*, and the scheduled actions
of *Social Media Sync*.

It asks LinkedIn for nothing the connector does not already ask for. Reading
the feed of a page, its comments and its reactions travels on
`r_organization_social`, which *Social Media Linkedin* requests on its own,
granted by the Community Management API product that connector already needs.

What does not follow on its own is the accounts already associated. **An
access token keeps the scopes it was issued with**, so an account authorized
before that permission was requested does not hold it and its history cannot
be imported until it is authorized again. Refreshing the token is not enough:
open the account, press *Update account* with **Update keys** ticked and
authorize on LinkedIn again.

The accounts concerned say so themselves, so nothing has to be looked up: a
warning is drawn on the account form for as long as the permission is missing,
the responsible user is notified by the check that runs every two hours, and
the import refuses with the name of the missing permission instead of the bare
error LinkedIn answers.

System parameters
---------------

One key is worth knowing about, and it is only written by hand in *Settings* >
*Technical* > *Parameters* > *System Parameters*: until then the module uses
the default the code carries. It is bounded when it is read, so a value outside its range is
brought back into it.

| Parameter | Default | Unit | Bounds |
| --- | --- | --- | --- |
| `social_media_linkedin_sync.posts_max_pages` | 50 | pages of 100 publications | 1 to 500 |

It is how far into the feed of a page one pass reads. The default covers five
thousand publications, and it is not a limit of LinkedIn: it is what keeps a
feed that never ends from looping forever.

**A page with a longer history has to raise it.** A feed read short comes back
partial, and the weekly full resync — the only pass that notices a publication
deleted on LinkedIn — does not look for deletions in a feed it could not read
whole. Nothing breaks and nothing is said beyond a warning in the log naming
the number of pages, so the symptom is publications that stay *posted* in Odoo
after being deleted on LinkedIn.

Raising it costs calls: each page is one call against the Posts API, so 500
pages are 500 calls per pass of every account, plus what reading their figures
adds. That is why the ceiling exists.
