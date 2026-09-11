Publishing options are not configurable
---------------------------------------

- The visibility, the feed distribution, the targeting by country, language or
  industry and the third party distribution are fixed in the code, so a
  publication cannot be restricted nor targeted from Odoo. Offering them means
  exposing them on the post and validating the combinations LinkedIn accepts.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api

Duration, codecs, dimensions and aspect ratio of a video are not checked
--------------------------------------------------------------------------

- Odoo does not read them before uploading: those limits are the ones of the
  [Videos API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/videos-api)
  and LinkedIn applies them while processing, so a video that breaks one of
  them is transferred whole and rejected afterwards, in the processing phase,
  with *LinkedIn could not process the video*. The size, 500 MB, and the MP4
  format are checked in Odoo, on the post while it is written and again before
  the publication is sent.

Rate limits are not handled
---------------------------

- The module does not handle the
  [throttle limits](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)
  of LinkedIn, applied per day and per application. When LinkedIn answers with
  a limit error, the operation is recorded as failed like any other error and
  has to be retried later by hand; only a credential rejection triggers an
  automatic retry, and only once.
