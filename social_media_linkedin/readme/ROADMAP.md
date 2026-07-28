Like the comments
-----------------

- To like a comment you need the scopes:

  * w_member_social_feed,
  * r_organization_social_feed
    Which are special permissions granted by LinkedIn

Comments on publications
------------------------

- Images, videos, documents, or any type of media are not allowed
  in post comments via the API, due to LinkedIn's own limitations.
  Although there is an example of how to do it in the documentation,
  in practice it doesn't work, even in paid versions.

Campaign objectives
-------------------

- LinkedIn defines seven campaign objectives: brand awareness, video views,
  website visits, engagement, lead generation, website conversions and job
  applicants.
- Only the first four are offered by this module. The other three need a
  configuration that lives on LinkedIn and that the module does not create
  nor check: lead generation needs a lead gen form, website conversions need
  conversion tracking, and job applicants needs LinkedIn Talent Solutions and
  is not compatible with the video format. Selecting them without that
  configuration is refused by LinkedIn when the campaign is created.
- Campaigns imported from LinkedIn keep their real objective; the ones that
  are not offered here are simply not shown in the field.

Post with video or image
------------------------

- The Posts API only supports creating a post with either images or a video,
  not both at the same time: the `content` of a post holds a single `media`
  entry. When a post carries a video, its images are ignored.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-07&tabs=http#post-schema

Sponsored posts with several images
-----------------------------------

- A post with more than one image is published as a multi-image post, and
  LinkedIn does not sponsor that format. Linking such a post to a campaign is
  refused before publishing, so the post is not left online without its ad.
- Publish the post with a single image if it has to be sponsored.

Video processing
----------------

- LinkedIn processes an uploaded video before it can be published, so
  publishing a post with a video waits until the video is available. The wait
  can be tuned with the `social_media_linkedin.video_poll_attempts` and
  `social_media_linkedin.video_poll_delay` system parameters (30 attempts
  every 2 seconds by default). A long video may need more than that.
