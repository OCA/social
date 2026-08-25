List of posts generated from Odoo.
---------------

Only posts generated using Odoo are displayed.

- Go to *Social Media* > Post

Generate a post.
---------------

This feature acts as a template for generating multiple posts
from a single view, depending on the selected accounts.

- Go to *Social Media* > Post > New or Go to *Social Media* > Dashboard > Add Post
- Fill in the required fields
- When the post is created, every X account of the active company is selected
  by default in *Accounts*; review the list and remove the ones you do not want
  to use before saving.
- Save
- Click on the *Post* button

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
- Select the account
- Click on the *Archive account* button
- Please note that all data associated with this account will be archived.
- To use an archived account again, open it in *Social Media* > Configuration >
  Accounts (*Archived* filter) and press *Unarchive account*: the account and
  its data are restored instead of creating a duplicate. *Update account* only
  reactivates it when *Update keys* or *Update token* is ticked, because those
  are the options that send the user back to X to authorize again. The
  *Associate Account* wizard is not the way to do it when the same API Key and
  API Secret are reused, because it refuses the keys already registered on
  another account, archived ones included.
- An archived account can be deleted permanently with the *Delete
  permanently* button, only available to a social media administrator. The X
  publications stay online, only the Odoo history is removed.

Enable since
------------------------
- Go to *Social Media* > Configuration > Accounts
- Select the account
- Select *Enable since*
- The *Post since* field is then enabled, allowing you to
  select the post to start the search for in the next post
  retrieval. Note that metrics for older posts will not be updated
  if this option is selected.

  ![ENABLE_SINCE](../static/img/readme/ENABLE_SINCE.png)

X limits and validations
------------------------

The module does not enforce the content limits of X: they are applied by X
when the publication is sent, so the failure is only seen at that moment.

- Odoo does not check the length of the message: X limits a publication to
  280 characters (more if the account has X Premium), see the
  [creation of a post](https://docs.x.com/x-api/posts/creation-of-a-post). If
  it is exceeded, the line is left as *Failed* with the error returned by X.
- X accepts at most **4 images or 1 video** per publication and does not allow
  mixing images and video in the same message, see the
  [media upload](https://docs.x.com/x-api/media/upload-media) documentation.
  Odoo does not validate it: if the post does not respect it, X refuses the
  publication and the reason is kept on the failed line.
- The size of the files is not checked either: the limits of X apply
  (about 5 MB per image, and 512 MB / 140 seconds per video). A bigger file
  makes the upload fail and the publication is left as *Failed*.
- Odoo does not filter the file picker by image or video format: it accepts
  any file of type ``image/*`` or ``video/*``. The actual formats X accepts
  are the ones described in the
  [media upload](https://docs.x.com/x-api/media/upload-media) documentation;
  a file X does not support is refused by X instead.
- A post is refused when it selects **two X accounts with the same username**:
  *There are X accounts with the same username (...), please check to avoid
  spam errors.* X rejects the same content sent twice from the same account
  for spam reasons, see the
  [creation of a post](https://docs.x.com/x-api/posts/creation-of-a-post), so
  the post is stopped in Odoo instead of failing halfway through.

Rate limits
------------------------

- The [rate limit](https://docs.x.com/x-api/fundamentals/rate-limits) is
  tracked per endpoint (reading publications, publishing, comments and
  deletion). When X answers that it is exhausted, Odoo stores the window it
  returns and does not call that endpoint again until it expires: a notice is
  shown with the limit of the plan, the remaining requests and the time of the
  next attempt. If X does not say when the window resets, 60 seconds are
  assumed.
- If X refuses a publication because the requests of the plan are exhausted,
  the line is left as *Failed* with the message *X did not accept the post.
  The account may have reached the limit of requests of its plan: check the
  account and try again later.* It is not a content error: wait for the window
  to end and press *Post* again, which only sends the failed accounts.
- The X accounts are left out of the automatic check for updates that runs
  every 2 hours, to spare the requests of the plan. Their statistics are
  refreshed when the account is linked, with the *Update* button of the
  dashboard and with the weekly full resync.

Comments and dashboard actions
------------------------

- The comments of a publication are read with the
  [recent search](https://docs.x.com/x-api/posts/recent-search) endpoint of X,
  which only covers the **last 7 days**: the replies to older publications are
  not shown on the dashboard even though the post has them. Retweets and
  quotes are excluded as well, only the replies are listed.
- Before acting on a publication from the dashboard, Odoo checks on X that the
  post still exists. If it was deleted directly on X, the action stops, the
  publication is marked as *Deleted* in Odoo and the notice *The post does not
  exist or has been deleted.* is shown.
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
- The X specific data is lost, because Odoo drops the columns of an
  uninstalled module: the API Key, the API Secret and the OAuth 1 tokens.
- The identifier of each account and publication on X is kept, so installing
  the module back and associating the account again reactivates the archived
  history and updates it, instead of importing everything as duplicated
  records.
