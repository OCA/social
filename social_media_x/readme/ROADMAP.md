- Recommending a publication or a comment is not implemented. X does offer the
  endpoints, `POST /2/users/:id/likes` and `DELETE /2/users/:id/likes/:tweet_id`,
  and a comment on X is a post like any other, so both would be the same call;
  what X withdrew is their access from the **Free tier**, and this module
  requires a paid plan anyway. Until the connector implements them the button
  is not shown for the X publications, neither on the publication nor on its
  comments.

  * Likes endpoints: https://docs.x.com/x-api/posts/likes/introduction

- An X account has no time series, so it draws nothing in *Social Media* >
  Statistics. The API v2 only answers the lifetime counters of the account, with
  no way of asking for them grouped by day. Giving X a series means either
  repeating the lifetime counter on every day, which draws a cumulative curve
  of a different shape than the other social media in the same graph, or
  storing the delta between two readings, which is false for any day the cron
  did not run. Neither is a measurement. If X ever published figures per day,
  implementing `_snapshot_statistics` in this connector is all it would take.

- The message of a post is checked against **280 characters**, the limit of
  the free X account. X Premium raises it to 25 000, so an account on that
  plan reads a warning about a post it could publish perfectly well. The plan
  is not in `social.account`, and X does not answer it with the user: it can
  only be deduced from what the API replies, which is what the connector
  already does after the fact in `_is_app_without_paid_plan`. Once the plan
  can be told apart before publishing, `_get_post_errors` already receives the
  account and the limit becomes per account. Meanwhile the check never blocks
  saving, so the post is still written and published.
