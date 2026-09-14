- Migrating a database where *Social Media X* held both halves needs a manual
  step. The stored fields `social.account.last_post_ref`,
  `social.account.enable_since` and `social.account.post_since_id` move from
  *Social Media X* to this module, and no migration script ships with it.
  Recreate the database, or update `ir_model_fields` so the three of them
  belong to this module before uninstalling the connector: Odoo drops the
  columns of the module that declares them, so an uninstall of *Social Media
  X* against the old ownership takes the checkpoint of the import with it.

- Recommending a publication or a comment is not implemented. X does offer the
  endpoints, `POST /2/users/:id/likes` and `DELETE /2/users/:id/likes/:tweet_id`,
  and a comment on X is a post like any other, so both would be the same call;
  what X withdrew is their access from the **Free tier**, and these modules
  require a paid plan anyway. Until they are implemented the button is not
  shown for the X publications, neither on the publication nor on its
  comments.

  * Likes endpoints: https://docs.x.com/x-api/posts/likes/introduction

- Deleting a comment is not implemented either, even though it is the same
  `DELETE /2/tweets/:id` call already used to delete a publication: the button
  is hidden client-side until a connector overrides `canDeleteComment`.

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
