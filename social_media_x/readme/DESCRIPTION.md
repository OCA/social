This module provides the necessary functionality for
basic interaction with the X social media.

Main features:
- User account integration.
- Post creation.
- Comments of a publication, read from the dashboard: X answers the whole
  conversation at once, so the replies of a comment are nested from what was
  already read instead of being asked for apart. A comment answers the
  publication, and answering a comment answers that comment, which on X is a
  post like any other.
- Reports with agnostic metrics, on the account form.
- What X will not publish, shown on the post while it is written. The message
  is checked against **280 characters**, and the medias against **4 images** of
  at most **5 MB** each — **15 MB** for a GIF — in JPG, PNG, WEBP or GIF, and
  **one video** of at most **512 MB** in MP4. X takes images or a video, never
  both in the same post, so a post mixing them is refused instead of warned
  about. The same checks refuse the publication if the post reaches it anyway,
  through an import or an RPC call.

*Recommend* is not offered on X, neither on a publication nor on a comment.
X does serve the endpoints — `POST /2/users/:id/likes` and
`DELETE /2/users/:id/likes/:tweet_id`, and a comment is a post like any other,
so both would be the same call — but it
[withdrew their access from the Free tier](https://devcommunity.x.com/t/update-to-x-api-free-tier-removal-of-like-and-follow-endpoints/247646).
This connector does not implement them, and until it does the button is not
rendered for the X publications. The roadmap says the rest.


Statistics account
-------------------
In the case of X statistics, only current posts are taken into account; if
some are deleted, the metrics also decrease, that is, it is not a
history of the account's posts.

The metrics are computed on the **100 most recent publications** X answers in
a single request, and only on original publications: retweets, replies and
quotes are discarded both when importing and when computing. The publications
older than those 100 are not counted, because the timeline
(`GET /2/users/:id/tweets`) is read once and not paginated, in order to spare
the requests of the plan.

1. The eye icon: Total number of views, which may include multiple views by the same user.
2. The hand icon: means the interactions (likes, comments, retweets and quotes)
   of current posts. They are the
   [metrics](https://docs.x.com/x-api/fundamentals/metrics) X returns for a post.
3. The star icon: means the value of the engagement of the publications, it is a calculation
   similar to (interactions / impressions) * 100.

   ![STATISTICS_ACCOUNT](../static/img/readme/STATISTICS_ACCOUNT.png)

If the X API [rate limit](https://docs.x.com/x-api/fundamentals/rate-limits) is
reached while refreshing the statistics, the last metrics stored on the
account are kept instead of failing.

**An X account draws nothing in *Social Media* > Statistics.** That screen reads a
history per day, and the [metrics](https://docs.x.com/x-api/fundamentals/metrics)
the API v2 answers are the current lifetime counters of each post, with no way
of asking for them grouped by day. Repeating a lifetime counter on every day
would draw a curve that is a modelling fiction, not a measurement, so nothing
is written: an account of X shows the standard empty view there, and its
figures live on the account form, which is where they mean something.
