This module adds the advertising layer on top of *Social Media Base*: the
campaigns used to promote the posts, the groups that manage several campaigns
as a unit, the tags that classify them and the view of the ads served by the
social media.

Everything is generic, so it works with any social media. Each connector
module plugs its own social media through the extension hooks, and contributes
its own submenu under *Advertising*: campaign groups, campaigns and ads belong
to a single social media, so they are never listed mixed together.

Main features:

- Campaign groups and campaigns, linked to a social media, to its accounts
  and to the posts they promote.
- A second campaign field on a post, next to the Odoo marketing campaign
  (`utm.campaign`) that *Social Media Base* provides: the campaign of the
  social media itself, which holds the budget and the remote reference. The
  two are independent.
- Tags to classify the campaigns.
- Stages declared per social media, so every social media keeps its own status
  vocabulary for campaigns, campaign groups and ads instead of a hardcoded
  list.
- Ads view listing the sponsored creatives of the connected accounts with
  their status, their campaign and the post they promote.
- An extensible hook so each social media module can import its campaigns.
