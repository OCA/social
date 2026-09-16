Security groups.
---------------

- The module reuses the groups of *Social Media Base*.
- *Social Media / User: Own Accounts* sees only the campaigns he is
  responsible for, and can create campaign groups and tags but not delete
  them.
- *Social Media / Administrator* sees every campaign and is the only group
  that manages the stages.

Advertising environment.
---------------

- Go to *Social Media* > Configuration > Accounts, open an account and its
  *Advertising* tab.
- *Environment*, in the *Advertising* tab, tells the advertising API of the
  social media
  which entities it must answer for this account.
  - *Test* only sees the test advertising accounts of the application, their
    campaigns and their ads. Nothing is ever served to a real audience and
    nothing is ever billed, which is why it is the default.
  - *Production* sees the real advertising accounts. A campaign created from
    Odoo in this environment spends a real budget once it is activated in the
    campaign manager of the social media.
- **The environment does not affect the publication of posts.** A post
  published from an account set to *Test* is a real post on the social media,
  visible to everybody. The setting only governs the advertising features.
- The two environments never share an advertising account, so changing the
  environment drops the advertising account in use.
- The tab only shows up when an advertising connector module is installed for
  the social media of the account.

Stages.
---------------

- Go to *Social Media* > Configuration > Stages > `<social media>`, a menu
  every connector module contributes for its own social media.
- A stage mirrors a status the social media gives to a campaign, a campaign
  group or an ad. It belongs to one social media and one scope, set in the
  *Applies To* field.
- *Code* is the value the social media returns, for example `ACTIVE` or
  `PENDING_DELETION`. It is what the connector module matches when it imports,
  so it must be written exactly as the social media sends it.
- *Level* is the colour of the badge showing the stage.
- This module ships **no** stage: each connector module declares the stages of
  its own social media in its `data/` folder. Until a connector is installed,
  the *Stage* field has no option to choose from.

Connector modules.
---------------

- To resolve a remote status, call
  `self.env["social.stage"]._get_stage(media_type, applies_to, code)`. It
  returns the stage, or an empty recordset when the connector has not declared
  that code.
- To make a social media selectable on the campaigns, extend
  `social.advertising.campaign._available_campaign()` and append your own media type.
- To restrict the social media campaigns that can be linked to a post, extend
  `social.post._get_allow_social_campaign_domain()`.
- To freeze another field of the post once it is published, extend
  `social.post._get_locked_content_fields()`, as this module does with the
  social media campaign.
- To list the advertising accounts of a social media, extend
  `social.account._advertising_media_types()` with your own media type, which
  is what makes the *Advertising* tab show up, and implement
  `social.account._fetch_advertising_accounts()` returning one dict of values
  per advertising account, with `remote_ref`, `name` and `environment`. The
  generic module takes care of creating, updating and dropping the
  `social.advertising.account` records, and of keeping the one in use.
- To add what only your social media reports, inherit
  `social.advertising.account` and declare your own fields, as
  *Social Media Advertising Linkedin* does with the serving status.
- To show your records, contribute a menu named after your social media under
  `social_media_advertising.social_advertising_menu`, with one
  `ir.actions.act_window` per model filtered on
  `[("media_id.media_type", "=", "<your media type>")]`, and another one under
  `social_media_advertising.social_stage_root_menu` for your stages. Both
  menus of this module are only containers: they hold nothing until a
  connector fills them, and Odoo hides them meanwhile.
- To import the campaigns and the campaign groups of a social media,
  implement `social.account.action_import_campaigns()` and return `success`,
  `message` and the number of imported `groups`, `campaigns` and `ads`. It is
  what the *Fetch campaigns* button of the account calls.
- To list the ads, implement `social.account._fetch_ads()`, returning one
  dict of values per ad, each carrying its `remote_ref`, and
  `social.account._fetch_ad_refs()`, returning only the references: the first
  is what *Sync ads* mirrors, the second is the cheap call the six-hour cron
  checks with.
- To delete an ad on the social media, implement
  `social.advertising.ad._delete_remote_ad()` and answer
  `_compute_can_delete_remote_ad()` for the ads your API accepts a deletion
  on. Extend `_register_remote_ad_gone()` to leave on the archived ad the
  status your social media gives a deleted one, and `_advertising_ad_action()`
  to send the user back to the list of your own social media.
- To give a record its address on the social media, implement
  `_get_web_url()` on `social.advertising.account`,
  `social.advertising.campaign`, `social.advertising.campaign.group` or
  `social.advertising.ad`: the *Open ...* button of the form shows up as soon
  as it answers one.
