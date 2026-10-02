Campaign objectives that are not offered
---------------------------------------

- LinkedIn defines seven campaign objectives: brand awareness, video views,
  website visits, engagement, lead generation, website conversions and job
  applicants, as listed in the
  [campaigns documentation](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns).
- The last three are not offered. They need a configuration that lives on
  LinkedIn and that the module does not create nor check: lead generation
  needs a lead gen form, website conversions need conversion tracking, and job
  applicants needs LinkedIn Talent Solutions and is not compatible with the
  video format. Selecting them without that configuration is refused by
  LinkedIn when the campaign is created.

Targeting and bidding cannot be set from Odoo
---------------------------------------------

- The audience and the bidding strategy of a campaign are defined in the
  LinkedIn Campaign Manager, never from Odoo. Offering them means mapping the
  targeting criteria of LinkedIn and validating the combinations it accepts,
  which is a feature of its own.

Carousel ads
------------

- The format LinkedIn offers for several sponsored images is Carousel ads
  (`content.carousel` with an `adContext`, on a campaign whose format is set
  to carousel when it is created, see the
  [creatives documentation](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-creatives)).
  This module does not implement it, so a post with several images cannot be
  sponsored even though the platform allows that format.
- The refusal of a multi-image post is a restriction of the content format,
  not of the access level of the application nor of the advertising account:
  no LinkedIn plan sponsors a multi-image post.

Two references for the same creative
------------------------------------

- `social.post.account.creative_urn` and `social.advertising.ad.remote_ref`
  both hold the URN of a creative. The first one is written when a sponsored
  post is published, before any import, so it is kept as it is. Merging them
  is left for a later version.
