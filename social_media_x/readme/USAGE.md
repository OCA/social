List of posts generated from Odoo.
---------------

Only posts generated using Odoo are displayed.

- Go to *Social Media* > *Posts*

Generate a post.
---------------

This feature acts as a template for generating multiple posts
from a single view, depending on the selected accounts.

- Go to *Social Media* > *Posts* > New or Go to *Social Media* > *Dashboard* > Add Post
- Fill in the required fields
- When the post is created, every X account of the active company is selected
  by default in *Accounts*; review the list and remove the ones you do not want
  to use before saving.
- Save
- Click on the *Post* button
- A publication shares the images and the video of its post, so the dashboard
  card shows them, and its video indicator, as soon as X accepts the message.
  Nothing waits for an import.

Update token, API Key, API Secret and account data
---------------

- Go to *Social Media* > Configuration > Accounts
- Select the account
- Click on the *Update account* button

  ![BUTTON_UPDATE_ACCOUNT](../static/img/readme/BUTTON_UPDATE_ACCOUNT.png)

- In the wizard that appears, if none of the checkboxes are selected and the
  *Update* button is pressed, the system will update only the account's data.
- If the *Update keys* checkbox is selected, the current API Key and API Secret
  values will be displayed by default. Modify any of these values and authentication
  will be performed again through X to update these values and the token.

  ![UPDATE_KEYS](../static/img/readme/UPDATE_KEYS.png)

- Selecting the *Update token* checkbox will update the current token.

  ![UPDATE_TOKEN](../static/img/readme/UPDATE_TOKEN.png)


Archive Account X
----------------------------
- Go to *Social Media* > Configuration > Accounts
- Select the account and use the standard *Actions* > *Archive* entry of the
  account form.
- Please note that all data associated with this account will be archived.
- To use an archived account again, open it in *Social Media* > *Configuration* >
  *Accounts* (*Archived* filter) and use the standard *Actions* > *Unarchive*
  entry: the account and its data are restored instead of creating a
  duplicate. *Update account* only
  reactivates it when *Update keys* or *Update token* is ticked, because those
  are the options that send the user back to X to authorize again. The
  *Associate Account* wizard is not the way to do it when the same API Key and
  API Secret are reused, because it refuses the keys already registered on
  another account, archived ones included.
- An archived account can be deleted permanently with the *Delete
  permanently* button, only available to a social media administrator. The X
  publications stay online, only the Odoo history is removed.

X limits and validations
------------------------

What X refuses is checked in Odoo before the publication is sent. The post
shows the reason while it is being written, saving is never blocked, and the
publication of the account that raises the objection is refused instead of
being sent and failing on X. The same checks are applied when the post reaches
the publication through an import or an RPC call, so nothing gets past them.

- The message is checked against the characters the plan of the account
  allows: **280** without X Premium and **25 000** with it, see the
  [creation of a post](https://docs.x.com/x-api/posts/creation-of-a-post). The
  plan is the **X Premium** switch of the account form, declared by hand
  because nothing reads it back from X. A longer message is reported on the
  post and the publication is not sent. A post selecting several X accounts is
  measured against the strictest of them while it is written, and every
  publication against its own account when it is sent, so only the line that
  cannot publish is refused. An account marked as Premium without holding the
  subscription sends the post and X refuses it: that line is left as *Failed*
  with the reason.
- X publishes **4 images or 1 video** per publication and never both kinds in
  the same message, see the
  [media upload](https://docs.x.com/x-api/media/upload-media) documentation. A
  post mixing them is refused instead of being warned about, and so is one
  carrying more than four images or more than one video.
- The images are checked against the formats X publishes, **JPG, PNG, WEBP and
  GIF**, and against **5 MB** each, **15 MB** for a GIF. The video is checked
  against **MP4** and **512 MB**. The message names the files that cannot be
  published.
- The file picker is not filtered: it accepts any file of type ``image/*`` or
  ``video/*``, and the check is what refuses the ones X does not take.
- The duration of the video is not checked in Odoo: a video X considers too
  long is refused by X and the line is left as *Failed* with the error it
  returned.
- A post is refused when it selects **two X accounts with the same username**:
  *There are X accounts with the same username (...), please check to avoid
  spam errors.* X rejects the same content sent twice from the same account
  for spam reasons, see the
  [creation of a post](https://docs.x.com/x-api/posts/creation-of-a-post), so
  the post is stopped in Odoo instead of failing halfway through.

Rate limits
------------------------

- The [rate limit](https://docs.x.com/x-api/fundamentals/rate-limits) is
  tracked per endpoint. The ones this module spends are linking the account,
  refreshing the data of the account, publishing (message and media upload),
  deleting, reading a single post and reading the figures of the recent ones
  (`get_posts`); a synchronization module adds its own to the same record.
  When X answers that it is exhausted, Odoo stores the window it returns and
  a notice is shown with the limit of the plan, the remaining requests and
  the time of the next attempt. That stored window is what stops a deletion,
  a check of a single post and a refresh of the figures before they are
  attempted; linking the account and publishing are tried all the same and
  report the limit only once X has refused them, and the refresh of the data
  of the account does not track its limit at all. If X does not say when the
  window resets, 60 seconds are assumed.
- If X refuses a publication because the requests of the plan are exhausted,
  the line is left as *Failed* with the message *X did not accept the post.
  The account may have reached the limit of requests of its plan: check the
  account and try again later.* It is not a content error: wait for the window
  to end and press *Post* again, which only sends the failed accounts.
- A deletion the window does not let happen stops with the message *The post
  could not be deleted on X. The account may have reached the limit of
  requests of its plan: check the account and try again later.*, and the
  publication stays in Odoo. Deleting the line while the tweet is still on X
  would leave the publication with nothing pointing at it, so the deletion
  waits for the window to end.
- Opening a publication, from its form or from its card on the dashboard,
  reads the tweet on X first. One deleted there answers *Not Found* and the
  publication is marked as *Deleted* on the spot, keeping its reference. The
  read spends one request of the plan and respects the same window as the
  rest: while the limit of the `get_post` endpoint is exhausted the
  publication is left untouched rather than asked about.
- The X accounts are walked by the automatic check for updates that runs every
  2 hours, which by itself asks X for nothing: the token of X does not expire
  and its API reports no figures by day, so the pass only hands the accounts
  over to whoever synchronizes them. Without a synchronization module
  installed nothing happens on that pass.

Figures of a publication
------------------------

- The figures of the posts published in the last 30 days — likes, replies,
  impressions, retweets and quotes — are read back from X once a day, by the
  *Social: Refresh the statistics of the recent publications* scheduled action,
  and on the spot by the *Update* button of the dashboard and *Update
  statistics* of the account form.
- Nothing walks the timeline to do it: Odoo already knows the identifier of
  every post it asks about, so they are read by batches of **100 ids per
  request** on its own `get_posts` endpoint. Reading the timeline is what
  imports what Odoo did not publish, and that is a synchronization module.
- Daily and not every two hours because the figures of a publication move
  slowly while the quota of the plan is counted per day: the window is what
  bounds what a run spends and the interval is what bounds how many runs
  there are. For the same reason the buttons read the same bounded window and
  never the whole account.
- While the window of `get_posts` is exhausted the pass asks X for nothing and
  the publications keep the figures they have, with the date of the reading
  they come from. What was read before the limit was reached is kept: those
  requests are spent either way.
- A post missing from the answer is left untouched. X does not report a post
  that was deleted or hidden, which is not the same as a post whose figures are
  zero, so its line keeps its last figures and its date.

Dashboard actions
------------------------

- Deleting a publication from the dashboard deletes the post on X first. If X
  refuses the deletion, the operation is cancelled with the error returned by
  X and the publication keeps existing both on X and in Odoo.
- The direct calls to X made while linking the account (token requests and
  download of the profile image) have a timeout of 10 seconds. If the connection
  or X take longer, the association fails and has to be repeated.

X credentials
------------------------

The [OAuth 1.0a](https://docs.x.com/resources/fundamentals/authentication/oauth-1-0a/api-key-and-secret)
tokens of X do not expire, so there is nothing to renew: they
only stop working when the access is revoked from the X application or the
keys are changed. When that happens X refuses the publication, the reason is
kept on the failed publication and the account is marked as needing an
update. Odoo cannot renew it by itself: associate the account again from
*Update account*.

Uninstalling the module
------------------------

Uninstalling *Social Media X* does not delete the accounts nor their
publication history:

- The access tokens are cleared, so no credential outlives the module.
- The X accounts are archived, together with their posts.
- The X specific data of this module is lost, because Odoo drops the columns
  of an uninstalled module: the API Key, the API Secret, the OAuth 1 tokens,
  the app-only bearer token, the rate limit window of each endpoint and the
  *X Premium* switch, which has to be ticked again after reinstalling. The
  fields of a synchronization module go with that module, not with this one.
- The identifier of each account and publication on X is kept, so installing
  the module back and associating the account again reactivates the archived
  history and updates it, instead of importing everything as duplicated
  records.
