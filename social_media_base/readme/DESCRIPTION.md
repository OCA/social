This module provides the fundamental foundation for social media management.
It facilitates the integration of user accounts, posts, reactions (likes),
comments, and graph-based analysis. Designed to be flexible and scalable,
it allows developers and businesses to integrate and customize social features
according to their needs.

Main features:

- Integration of multiple user accounts.
- Basic methods that can be extended and adapted to suit the social network.
- Basic business structure.
- Campaign group and campaign structure linked to posts, with an extensible
  hook so each social network module can import its campaigns.
- Dashboard of published posts with campaign, video and deletion indicators.
- Scheduled synchronization of post statistics (monthly cron), plus an
  initial synchronization right after an account is linked.
- Account credentials (OAuth tokens) are only visible to administrator users.
