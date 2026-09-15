This module publishes on the LinkedIn company pages an Odoo user
administrates, and keeps the daily figures of those pages.

Everything it asks LinkedIn for costs a fixed number of calls per account or
per publication, so what it costs does not change whether a page published
once or ten thousand times. Reading back what the page already published ---
importing the publications, their comments and their reactions --- grows with
that history and lives in *Social Media LinkedIn Sync*, which installs on its
own as soon as *Social Media Sync* is present.

Main features:
- Integration of the LinkedIn company pages (organizations) the user
  administrates; personal profiles are not supported.
- Post creation, with images or a video: LinkedIn publishes either the images
  or the video, never both.
- Daily statistics of the page: the figures LinkedIn reports by day are
  written as a time series, with reports and native graph and pivot views over
  them. It costs a fixed number of calls per account, decided by the width of
  the window asked for and not by what the page published: one call for the
  refresh of the last days, a handful for the whole period LinkedIn reports,
  because the figures asked for are those of the whole organization and the
  URNs of the publications never enter the query.
- What LinkedIn will not publish, shown on the post while it is written. The
  message is checked against **3000 characters**, and the medias against **20
  images** of at most **10 MB** each in JPG, PNG or GIF, and **one video** of
  at most **500 MB** in MP4. A post carrying a video is published without its
  images, so with a video none of the image rules apply and the post is warned
  that only the video goes out. The same checks refuse the publication if the
  post reaches it anyway, through an import or an RPC call.


Statistics account
-------------------
1. The eye icon: Total number of views, which may include multiple views by the same user.
2. The hand icon: the interactions (clicks, likes, comments and shares) the
   page accumulated over the days of the series.
3. The star icon: the engagement of the account, its interactions over its
   impressions, shown as a percentage. The engagement LinkedIn reports by day
   is kept on each row of the time series and read in the graph and pivot
   views; it is never averaged into the card.

   ![STATISTICS_ACCOUNT](../static/img/readme/STATISTICS_ACCOUNT.png)
