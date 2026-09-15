List of posts generated from Odoo.
---------------

Only posts generated using Odoo are displayed.

- Go to *Social Media* > Posts
- Opening a publication, from its form or from its card on the dashboard,
  reads it on LinkedIn first. One that was deleted there is reported as *The
  post does not exist or has been deleted.* and marked as *Deleted* on the
  spot, keeping its reference. Only a `404` counts as a deletion: a lost page
  role or a throttled application leaves the publication alone, because a
  publication is not gone just because Odoo could not read it.

Generate a post.
---------------

This feature acts as a template for generating multiple posts
from a single view, depending on the selected accounts.

- Go to *Social Media* > Posts > New or Go to *Social Media* > Dashboard > Add Post
- Fill in the required fields
- When the post is created, every LinkedIn account of the active company is
  selected by default in *Accounts*; remove the ones you do not want to use
  before publishing.
  ![CREATE_POST](../static/img/readme/CREATE_POST.png)
- Save
- Click on the *Post* button
- LinkedIn publishes either images or a video, never both: when the post
  carries a video, its images are left out. The preview of the post says so
  by showing the video alone, so what is previewed is what LinkedIn
  receives, and a banner on the form explains it as well.
- A publication shares the images and the video of its post, so the dashboard
  card shows them as soon as LinkedIn accepts the post and nothing else has to
  run. What LinkedIn made of each media is recorded on the publication, which
  is what lets an image deleted on LinkedIn leave the card while the one in the
  post stays; noticing that deletion needs *Social Media LinkedIn Sync*.

Update token, client ID, client Secret and organization data
---------------

- Go to *Social Media* > Configuration > Accounts
- Select the account
- Click on the *Update account* button

  ![BUTTON_UPDATE_ACCOUNT](../static/img/readme/BUTTON_UPDATE_ACCOUNT.png)

- In the wizard that appears, if none of the checkboxes are selected and the
  *Update* button is pressed, the system will update only the organization's data.
- If the *Update keys* checkbox is selected, the current Client ID is proposed
  to the administrator users, the only ones allowed to read it, and the Client
  Secret has to be typed again: the stored secret is never sent to the browser.
  Authentication is then performed again through LinkedIn, and the keys are
  only written on the account once LinkedIn has accepted them, so an
  authorization left halfway keeps the credentials that still work.

  ![UPDATE_KEYS](../static/img/readme/UPDATE_KEYS.png)

- Selecting the *Update token* checkbox will update the current token.

  ![UPDATE_TOKEN](../static/img/readme/UPDATE_TOKEN.png)

Validate the token
---------------

- Go to *Social Media* > Configuration > Accounts
- Select the account and open the *Configuration* tab
- Click on the *Validate token* button. It always asks LinkedIn whether the
  token is still active, because a token can be revoked there long before
  the stored expiry dates: a notification confirms that it is valid, and if
  it is not, the token is renewed. Outside the renewal window, the check made
  before every call to LinkedIn uses the stored dates, so it costs no extra
  request.

  ![VALIDATE_TOKEN](../static/img/readme/VALIDATE_TOKEN.png)

Archive Account Linkedin
----------------------------

- Go to *Social Media* > Configuration > Accounts
- Select the account and pick *Archive* in the *Actions* menu of the form.

  ![ARCHIVE_ACCOUNT](../static/img/readme/ARCHIVE_ACCOUNT.png)

- Please note that all data associated with this account will be archived.
- If you associate the same LinkedIn account again later, the archived
  account and its related data will be reactivated instead of creating a
  duplicate.
- An archived account can be deleted permanently with the *Delete
  permanently* button, only available to a social media administrator. The
  LinkedIn publications stay online, only the Odoo history is removed.

Uninstalling the module
----------------------------

Uninstalling *Social Media Linkedin* does not delete the accounts nor their
publication history:

- The access token and the refresh token are cleared, so no credential
  outlives the module.
- The LinkedIn accounts are archived, together with their posts.
- The LinkedIn specific data is lost, because Odoo drops the columns of an
  uninstalled module: the application Client ID and Client Secret.
- The identifier of each account and publication on LinkedIn is kept, so
  installing the module back and associating the account again reactivates
  the archived history and updates it, instead of importing everything as
  duplicated records.

Time series of the account
---------------

- LinkedIn is asked for its figures **by day**, with the
  [`organizationalEntityShareStatistics`](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/organizations/share-statistics)
  finder and `timeGranularityType=DAY`, and every bucket it answers becomes
  one row of *Social Media* > Statistics. Nothing is invented for the days it
  reports nothing for.
- Right after the account is linked, the rewrite window is read and the whole
  period LinkedIn reports is asked for straight after, so the card of the
  dashboard is filled with the year and not only with the last days. No
  synchronization module is needed for that.
- The finder answers at most 100 daily buckets per call and does not paginate,
  so a period wider than that is asked for in several calls, one after
  another, instead of coming back cut at the hundredth day.
- The whole period is read only once. It is then skipped, because the rewrite
  window is the only thing written on every pass and a row older than it can
  only come from that first reading. If it failed --LinkedIn refused the call,
  the token had just been issued-- the *Rebuild statistics history* button of
  the account form asks for it again.
- The last week is asked for again on every pass of the two-hourly check,
  and by the *Update statistics* button of the account form. LinkedIn
  revises figures of days already past, so the recent ones are rewritten
  instead of being trusted as final; the days before that window stay as
  they were left.
- The *Rebuild statistics history* button asks LinkedIn for the daily figures
  of the page again, as far back as it reports them, and rewrites the time
  series with them. It **does not import publications**: what it rebuilds is
  the graph of the account. Bringing in the publications themselves is what
  *Social Media LinkedIn Sync* does.
- An account whose statistics LinkedIn refuses is reported and skipped, and
  the rest of the accounts keep the rows already written for them.
- The account is asked for its organization page as a whole, which includes
  what was published before Odoo managed the account or outside of it. The
  figures are therefore not the sum of what Odoo imported and are not meant
  to be compared against it.

Figures of a publication
---------------

- The figures of the publications of the last 30 days are read back from
  LinkedIn once a day, by the *Social: Refresh the statistics of the recent
  publications* scheduled action, and on the spot by the *Update* button of the
  dashboard and *Update statistics* of the account form.
- Nothing walks the feed to do it: Odoo already knows the URN of every
  publication it is asking about, so a whole page of them is answered by **at
  most three calls** — `organizationalEntityShareStatistics` once for the shares
  and once for the UGC posts, and `socialActions` for the likes and the comments
  of the UGC posts, which LinkedIn documents as the up-to-date ones.
- Only the kinds the page really carries are asked for. The publications Odoo
  publishes are shares, so a page of them costs **one call**: the finder answers
  their likes and comments inside the same block, and `socialActions` is only
  asked about UGC posts, which are the publications made outside Odoo.
- Those URNs travel in the query string of a finder LinkedIn documents as not
  paginated, so a page whose URNs do not fit in 4 KB is asked for in as many
  calls as it takes, around 95 publications each. That is the only thing that
  adds a call to the three.
- A publication missing from the answer is one nobody interacted with: the
  finder leaves out the entities with no activity at all, so its figures are
  written as zeros and its date as read all the same.
- No new permission is needed: the figures of a publication come from
  `organizationalEntityShareStatistics` and `socialActions`, which the scopes
  already requested when the account was associated cover, so an account
  already associated is not asked to authorize anything again.
- Reading the publications LinkedIn has and Odoo does not is another matter,
  and it stays in *Social Media LinkedIn Sync*: that one costs one call per
  page of the feed.

LinkedIn tokens
---------------

- The access token of LinkedIn lasts two months and its refresh token a year,
  as stated in the
  [refresh tokens documentation](https://learn.microsoft.com/en-us/linkedin/shared/authentication/programmatic-refresh-tokens).
  Within the week before the expiry date, and on every run of the scheduled
  action *Social: Checking social media updates* and before publishing, Odoo
  asks LinkedIn whether the token is still active (`introspectToken` endpoint)
  and only renews it when LinkedIn answers that it is not. Outside of that
  window the check is answered with the stored dates and costs no request.
  Nothing has to be done for a post planned weeks ahead.
- If LinkedIn refuses the token anyway, it is renewed and the publication is
  sent again straight away.
- Once the refresh token expires, or the authorization is revoked from
  LinkedIn, no renewal is possible: the account shows the update warning and
  has to be authorized again with *Update account*, which is the only step
  that needs the browser.

LinkedIn limits and validations
---------------

What LinkedIn refuses is checked in Odoo before the publication is sent. The
post shows the reason while it is being written, saving is never blocked, and
the publication of the account that raises the objection is refused instead of
being sent and failing on LinkedIn. The same checks are applied when the post
reaches the publication through an import or an RPC call, so nothing gets past
them.

- The message is checked against **3000 characters**, the length the
  `commentary` field of the
  [Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api)
  takes. A longer message is reported on the post and the publication is not
  sent.
- The images are checked against **20** per post, against the formats LinkedIn
  publishes, **JPG, PNG and GIF**, and against **10 MB** each. One image is
  published as a single image and two or more as a
  [multi-image post](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/multiimage-post-api).
  The message names the files that cannot be published.
- The video is checked against **one** per post, against **MP4** and against
  **500 MB**.
- A post carrying images and a video is not refused: LinkedIn publishes the
  video and leaves the images out, so the post is told what goes out instead
  of being stopped. That is also why the image rules are not applied at all to
  a post carrying a video — its images decide nothing.
- The file picker only filters what the browser proposes, so a file added by
  drag and drop reaches the checks all the same, and they are what refuses the
  ones LinkedIn does not take.
- What is left to LinkedIn is everything about the content itself: the
  dimensions and the aspect ratio of an image, the codecs and the duration of
  a video, the text it reads as spam. Nothing of that is checked here, and a
  publication LinkedIn refuses for one of those reasons is left as *Failed*
  with the validation error it answered.
- Every call to LinkedIn has a timeout of **10 seconds**, not configurable. If
  LinkedIn or the connection take longer, the operation fails with *Error
  connecting to LinkedIn* and has to be retried; a publication is left as
  *Failed* and can be sent again with the *Post* button.
- An account without an access token does not publish: this is what happens
  after uninstalling and installing the module back, which clears the
  credentials. The line is left as *Failed* stating that the account has no
  access token, and the account shows the update warning. Authorize it again
  with *Update account*.
- Recommending a publication or one of its comments, and reading those
  comments back, is served by *Social Media LinkedIn Sync*: this module draws
  none of those buttons and never calls the Reactions API.
- Deleting a publication from the dashboard deletes it on LinkedIn first. If
  LinkedIn does not confirm the deletion, the operation is cancelled with
  *Error deleting LinkedIn post* and the record is kept in Odoo, so the two
  sides never get out of sync.

Video upload
---------------

- LinkedIn decides how a video is split: `initializeUpload` answers one
  instruction per part, of 4 MiB each except the last one, and every part is
  uploaded with its own request. The identifiers LinkedIn returns for the
  parts are sent back to `finalizeUpload` in the same order, so the video is
  put together as it was cut. A 22 MB video takes 6 parts, and publishing
  then waits for LinkedIn to finish processing it, up to 30 polls two seconds
  apart.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api

- A post publishes a single video, so a post carrying several is refused
  before uploading anything: LinkedIn would only keep the first one and the
  others would be transferred and processed for nothing.
- LinkedIn processes an uploaded video before it can be published, so
  publishing a post with a video waits until the video is available: 30
  attempts every 2 seconds, which a long video may need more than. Both
  numbers are system parameters, described in CONFIGURE.
- The publication shares the video of its post the same way it shares its
  images, and what LinkedIn made of it is recorded in its media references.
  The camera icon without a count is the fallback drawn for a publication
  that carries only the *has video* flag — one imported from LinkedIn, whose
  video was never downloaded and can only be watched there.

Publishing options
---------------

- Every publication is created **public**, in the main feed, with no targeting
  by country, language or industry, and letting it be shared: `visibility`,
  `feedDistribution`, `targetEntities` and `thirdPartyDistributionChannels`
  are fixed in the code.
- Scheduling is not delegated to LinkedIn either: the Odoo scheduled action is
  the one that publishes when the date arrives.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

Errors reported by LinkedIn
---------------

- When LinkedIn rejects a request because of its content, its answer only
  says that the validation failed and lists the rejected fields apart, in
  the shape described in its
  [error handling guide](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/error-handling).
  Those explanations are the ones shown in Odoo, one per line, so the
  message names the field and the rule that was broken instead of the
  generic summary.
