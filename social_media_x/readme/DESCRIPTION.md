This module provides the necessary functionality for
basic interaction with the X social network.

Main features:
- User account integration.
- Post creation.
- Post reactions (likes, comments).
- Comment reactions (likes)
- Reports and graphs with agnostic metrics.


Statistics account
-------------------
In the case of X statistics, only current posts are taken into account; if
some are deleted, the metrics also decrease, that is, it is not a
history of the account's posts.

1. The eye icon: Total number of views, which may include multiple views by the same user.
2. The hand icon: means the impressions (likes, comments, shares, retweets, quote_count)
   of current posts.
3. The star icon: means the value of the engagement of the publications, it is a calculation
   similar to interactions / (impressions * 100).

   ![STATISTICS_ACCOUNT](/social_media_linkedin/static/img/readme/STATISTICS_ACCOUNT.png)
