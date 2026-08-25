Kanban view of the campaigns.
---------------

The `fold` field of `social.stage` is meant for a kanban of the campaigns
grouped by stage, which is not implemented yet. Until then the field has no
visible effect.

Tags without colour.
---------------

`social.tag` only has a name: it has neither a colour field for the
`many2many_tags` widget nor a uniqueness constraint on the name, so two tags
can share it.

Campaign groups and tags are shared data.
---------------

`social.advertising.campaign.group` and `social.tag` have no responsible and
no record rule, so every social media user sees and edits all of them, unlike
the advertising accounts, the campaigns and the ads, which are restricted to
their responsible. Scoping them is left for a later version.

Campaign visibility of a shared post.
---------------

The record rule of `social.advertising.campaign` restricts a user to the campaigns he is
responsible for. If an administrator assigns a post to a user and that post is
linked to a campaign of somebody else, the badge is empty for that user. A
finer rule, for instance sharing the campaigns of a campaign group, is left
for a later version.

Statistics of a single window.
---------------

There is no history per day, so the evolution of an ad cannot be charted: a
new synchronization replaces the statistics of the previous one. Charting it
needs a table of facts per day, the way `social_media_base` already keeps one
for the accounts in `social.account.statistics`, and giving the advertising
models the same treatment is a feature of its own.

`remote_ref` is writable through RPC.
---------------

The form views render `remote_ref` readonly, and on the ads and the
advertising accounts the ACL backs it: a social media user only reads them.
The campaigns and the campaign groups are the ones he writes, so on those two
he can still change or empty the field through RPC and orphan the record on
the social media. Restricting the field is a hardening candidate for a later
version.

Connector modules without an advertising layer.
---------------

Only LinkedIn has its advertising connector, *Social Media Advertising
LinkedIn*. The other connectors of the family, such as `social_media_x`, have
no advertising module yet: their accounts publish posts but do not manage
campaigns.

Records without a social media are out of every menu.
---------------

The lists of campaign groups, campaigns and ads are filtered on the social
media they belong to. A campaign saved without one, or a campaign group whose
campaigns mix social medias, which empties its media, is therefore reachable
only through a stat button or a saved filter.
