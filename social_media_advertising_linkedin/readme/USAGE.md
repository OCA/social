Choose the LinkedIn advertising account.
---------------

- Go to *Social Media* > Configuration > Accounts, open the LinkedIn account
  and its *Advertising* tab, then click *Fetch advertising accounts*.
- Besides the generic columns, the list shows what LinkedIn reports:
  - *LinkedIn Status*: `DRAFT`, `ACTIVE`, `CANCELED`, `PENDING_DELETION` or
    `REMOVED`.
  - *LinkedIn Serving Status*: `RUNNABLE` when the advertising account is
    eligible for serving, otherwise the reasons why it is not, such as
    `BILLING_HOLD`, `ACCOUNT_TOTAL_BUDGET_HOLD`, `ACCOUNT_END_DATE_HOLD`,
    `RESTRICTED_HOLD`, `INTERNAL_HOLD` or `STOPPED`. This is the column to
    look at when nothing is being served.
  - *LinkedIn Type*: `BUSINESS` or `ENTERPRISE`.
  - *LinkedIn Owner*: the organization or person the advertising account
    advertises on behalf of, which tells apart two advertising accounts
    sharing a name.
- *Campaign Manager URL* opens the advertising account on LinkedIn.
- *Create in LinkedIn*, *Fetch campaigns* and the sponsored creatives all
  work against the advertising account marked *In Use*.

Create a campaign in LinkedIn.
---------------

To link a post to a campaign, the campaign must already exist in LinkedIn:
only the campaigns already synchronized with LinkedIn are offered on the
post, and publishing one never creates the campaign it points at.

- Go to *Social Media* > Advertising > LinkedIn > Campaigns and open the
  campaign
- Fill in the campaign group, the account, the *Unit cost* and the *Daily
  budget*. Before calling LinkedIn, Odoo checks everything at once and shows
  the errors together: the unit cost, the daily budget of the campaign and the
  total budget of its group have to be **greater than zero**, and the group,
  the social account, the currency, the objective (required with the *Single
  video* format) and the political advertising declaration have to be set.
- A LinkedIn campaign can only point to **one LinkedIn account**: on LinkedIn
  a campaign belongs to a single advertising account. Adding a second one is
  refused when saving with *A LinkedIn campaign can only have one LinkedIn
  account.*
- Choose the *LinkedIn Ad Format*: *Standard update* for posts with text or
  images, *Single video* for posts with a video. LinkedIn fixes the format
  when the campaign is created and only accepts posts of that format
  afterwards, so a post with a video needs its own video campaign. The check
  works both ways: a *Single video* campaign **only** accepts posts carrying a
  video, and a post without one linked to it is refused before publishing with
  *The campaign ... only accepts posts containing a video*. The fields of a
  campaign are the ones of the
  [campaigns documentation](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns).
- The *Social campaign* field of the post only offers the campaigns matching
  what the post carries, so the format cannot be got wrong from the form: a
  post with a video is offered the *Single video* campaigns, and a post
  without one the *Standard update* campaigns. Campaigns imported without a
  format count as *Standard update*, like everywhere else in the module, and
  campaigns not created on LinkedIn yet are left out whatever the format.
- Attaching or removing the video of a post changes which campaigns it
  accepts. A campaign already chosen that no longer matches is cleared right
  there, so the mismatch is not discovered when the post is published.
- The *LinkedIn Objective* is required by LinkedIn for the video format. Four
  of the seven objectives LinkedIn defines are offered here: brand awareness,
  video views, website visits and engagement. A campaign imported from
  LinkedIn keeps its real objective, and the ones that are not offered here
  are simply not shown in the field. The ROADMAP says why the other three are
  left out.
- The campaign is always created as *Sponsored Updates*, with off-site
  delivery disabled and **without targeting criteria**: the audience is
  defined in the LinkedIn Campaign Manager, and LinkedIn does not let a
  campaign be activated without one.
- No bidding strategy is chosen from Odoo either, so the *Unit cost* only
  applies when the campaign uses manual bidding, target cost or cost cap in
  the Campaign Manager; with automatic bidding LinkedIn ignores it. Both are
  described in the
  [campaigns documentation](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns).
- A post with more than one image is published as a multi-image post, and
  LinkedIn does not sponsor that format: *"API partners can only create
  non-sponsored multiImage posts"*. Linking such a post to a campaign is
  refused before publishing, so the post is not left online without its ad,
  and the post form warns about it as soon as the campaign is selected.
  Publish the post with a single image if it has to be sponsored.

  https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/multiimage-post-api
- The *LinkedIn Political Intent* is the declaration LinkedIn requires to
  create any campaign since the EU political advertising regulation. It
  defaults to *Not political advertising*, which states that none of your
  ads qualify as political advertising under the law of the targeted
  countries, including EU law for ads targeted to the EU. Change it to
  *Political advertising* when they do.
- Click on the *Create in LinkedIn* button
- The campaign group and the campaign are created in LinkedIn in **DRAFT**
  status, so no budget is spent until you activate them from the LinkedIn
  Campaign Manager.
- If the campaign cannot be created, the error is shown in a notification
  and logged in the chatter instead of being raised: the campaign group is
  already created on LinkedIn, which does not allow deleting it, so its
  reference is kept to avoid importing it later as a duplicate. Fix the
  reported problem and press *Create in LinkedIn* again; the existing group
  is reused.
- A campaign group can also be created on LinkedIn on its own: open the
  group and click its *Create in LinkedIn* button (it requires a positive
  total budget and a currency). If you forget to do it, the group is
  created automatically when the first campaign of the group is published.
  The button only works once: if the group already has a LinkedIn reference,
  the action is refused with *The campaign group already exists on LinkedIn.*
  Use *Update in LinkedIn* to push later changes.
- A group has no account of its own: to create, update or archive it on
  LinkedIn, Odoo takes the advertising account from the campaigns of the
  group, and it never guesses. If the group has no campaign with an account
  and the database holds several LinkedIn accounts, or if its campaigns point
  to different accounts, the operation is refused; set the account on one of
  its campaigns first.
- The language and the country of the campaign (its locale) are taken from the
  form of the user who presses *Create in LinkedIn*: their language and the
  country of their company or contact. When the user has no country, `US` is
  sent. Check the user form before creating campaigns, because LinkedIn fixes
  that value when the campaign is created.
- The LinkedIn stages are installed as data of the module and listed in
  *Configuration* > Stages > LinkedIn. If they are deleted
  or their code is modified, creating or archiving a campaign or a group fails
  with *The LinkedIn stage with code ... for Campaign is missing*. Upgrading the
  module *Social Media Advertising LinkedIn* recreates a stage that was
  deleted, but not one whose code was modified: the stages are declared
  `noupdate`, so the module data never overwrites them. Put the code back by
  hand, or delete the record and upgrade the module.
- When a post linked to a campaign is published, it is attached to the
  campaign as a
  [sponsored creative](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-creatives).
  If the post is published but the creative
  cannot be linked, the post is kept and the error is logged in the chatter.
- The creative is created with an **active** intended status, unlike the
  campaign and the campaign group, which are created in draft. It therefore
  starts being served as soon as the campaign is activated in the Campaign
  Manager, with no further step in Odoo.
- A post with more than one image cannot be sponsored: LinkedIn publishes it
  as a multi-image post and does not accept that format as an ad, so linking
  it to a campaign is refused before publishing. The post form warns about it
  as soon as the campaign is selected, without waiting for the *Post* button.

Fetch campaigns from LinkedIn.
---------------

- Go to *Social Media* > Configuration > Accounts, open the LinkedIn account
  and its *Advertising* tab
- Click on the *Fetch campaigns* button
- The campaign groups, campaigns and their sponsored creatives are imported
  from LinkedIn Ads. Every creative is matched with the publication it
  promotes by its remote reference.
- A publication brought from the wall with *Update* has no post in Odoo, so
  its campaign is taken from the creative and its badge appears on the
  dashboard. Publications published from Odoo keep the campaign of their
  post and are never overwritten by the import.
- The Posts API does not return the campaign of a post, so only this import
  can resolve it. The order does not matter, but the publications have to be
  already in Odoo: if they are brought **after** importing the campaigns,
  press *Fetch campaigns* again.
- Campaign groups created on LinkedIn often carry no total budget, which is
  optional there, as described in the
  [campaign groups documentation](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaign-groups). Those groups set no limit in Odoo either: the rule keeping
  the daily budgets of the campaigns within the total budget of their group
  only applies when the group has one, and it is never checked on the values
  brought by the import. The rule is enforced from both sides: raising the
  daily budget of a campaign, moving it to another group, and lowering the
  total budget of a group are all refused when the sum goes over it.
- The *LinkedIn Ad Format* field only covers *Standard update* and *Single
  video*. A campaign created on LinkedIn with any other format (carousel,
  spotlight, text ad...) is imported into Odoo as *Standard update*, because
  that format does not exist in the field. Do not link publications to those
  campaigns: LinkedIn refuses the creative.
- The cost reported by the statistics of the ads is returned by LinkedIn in
  **US dollars** (`costInUsd`), even when the advertising account works in
  another currency: LinkedIn applies its own conversion, so it does not match
  the billing in the currency of the account exactly.
- The real LinkedIn status of each campaign and campaign group (Draft,
  Active, Paused, Archived...) is stored in its *Stage*, shown as a status
  bar on the form and refreshed on every import. Campaigns flagged as test
  campaigns on LinkedIn are marked as well.
- Campaigns and campaign groups deleted on LinkedIn (*Pending deletion*,
  *Removed*) are hidden in the LinkedIn Campaign Manager, but the API
  keeps returning them because of their performance data. They are
  therefore kept in Odoo as history, and a note is logged in their chatter
  when the deletion is detected. Keep in mind that deleting a campaign
  group on LinkedIn also deletes all its campaigns and ads.

Delete an ad in LinkedIn.
---------------

- The *Delete ad* button of an ad deletes it on LinkedIn. It needs the
  `rw_ads` scope, and the member who authorized the account has to hold an
  administrative role on the advertising account: a `VIEWER` cannot delete
  anything even with the scope granted.
- LinkedIn only deletes a
  [sponsored creative](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-creatives)
  outright when it is still a draft, when its campaign is, or when it is a
  video that failed to process. In that case the ad disappears from
  LinkedIn and its record is deleted in Odoo too, statistics included.
- Any other ad is not deleted on the spot: LinkedIn only takes the request
  and processes it afterwards. The creative is read back right away, so the
  status shown in Odoo is the one LinkedIn reports and not the one that was
  asked for, and the notification says which of the two happened.
- An ad with no statistics is dropped by LinkedIn as soon as the deletion is
  requested. Its record is then archived with the *Removed* status instead
  of waiting for the next *Sync ads*, and it stays as history like every ad
  that stops being answered.
- A creative already deleted keeps being returned by the API as *Removed*
  while it has performance data, exactly like the campaigns.
- The button is not offered on an ad whose status is *Archived*, *Canceled*,
  *Pending deletion* or *Removed*: LinkedIn accepts no change on those and
  answers *Cannot update a canceled creative*. Those ads stay in Odoo as
  history.

Update a campaign in LinkedIn.
---------------

- When you modify in Odoo the editable fields of a campaign (name, unit
  cost, daily budget, campaign group, political declaration) or of a
  campaign group (name, total budget, currency) that already exists on
  LinkedIn, the record shows a *Pending
  changes* ribbon, a warning banner explaining that the local changes have
  not been pushed yet, and an *Update in LinkedIn* button. A record that
  does not exist on LinkedIn yet carries no ribbon at all: the *Create in
  LinkedIn* button already says it. The tracked fields also
  log their changes in the chatter. The *Media* of a campaign is guarded the
  same way, so an archived campaign cannot be unlocked by taking it out of
  LinkedIn.

  ![CAMPAIGN_NOT_SYNCED](../static/img/readme/CAMPAIGN_NOT_SYNCED.png)

- Click *Update in LinkedIn* to push the local values to LinkedIn. To move
  the campaign to another campaign group, the target group must already
  exist on LinkedIn. The political advertising declaration is pushed the
  same way, since LinkedIn allows updating it when the targeting changes.
- Synchronization priority is hybrid: the LinkedIn-only fields (stage,
  test flag) are always refreshed by *Fetch campaigns*; for the editable
  fields, your local pending changes are preserved by the import — the
  LinkedIn values are logged in the chatter so you can decide whether to
  keep your changes (push them with *Update in LinkedIn*) or re-type the
  LinkedIn ones.
- When the LinkedIn stage is *Archived*, *Canceled*, *Pending deletion*
  or *Removed*, the campaign or campaign group cannot be modified in Odoo
  (LinkedIn does not allow editing them either): the editable fields
  become read-only, the *Update in LinkedIn* button is hidden and a red
  banner explains the situation. The *Media* of a campaign that exists on
  LinkedIn is read-only as well, so the lock cannot be escaped by taking the
  campaign out of LinkedIn. The import keeps refreshing their stage,
  so an archived record becomes editable again once it is unarchived on
  LinkedIn.

Archive a campaign or a campaign group in LinkedIn.
---------------

- LinkedIn does **not** allow deleting a campaign or a campaign group
  through its API, whose statuses are the ones of the
  [campaigns documentation](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-campaigns).
  Archiving is the only way to end them, and it is what the
  *Archive in LinkedIn* button does.
- Go to *Social Media* > Advertising > LinkedIn, open the campaign or the
  campaign group and click *Archive in LinkedIn*. The button is only shown when the
  record already exists on LinkedIn and is not already archived, canceled or
  deleted.

  ![CAMPAIGN_ARCHIVE](../static/img/readme/CAMPAIGN_ARCHIVE.png)

- LinkedIn refuses to archive a campaign while its campaign group is still
  in **Draft**: activate the group in the Campaign Manager first, or archive
  the group instead, which archives its campaigns. Odoo checks it before
  calling LinkedIn and explains it.
- A campaign or a campaign group still in Draft keeps the start date given
  when it was created, and LinkedIn rejects any later change because that
  date already belongs to the past. Odoo therefore sends a new run schedule
  when it updates or archives a record in Draft, which moves its start date
  to the moment of the change.
- The campaign stops running on LinkedIn and disappears from the Campaign
  Manager active lists, but it is kept in Odoo with its performance data.
  Its stage becomes *Archived*, which makes the record read-only in Odoo,
  because LinkedIn no longer accepts changes on it.
- **It cannot be reactivated from Odoo.** To unarchive it, use the LinkedIn
  Campaign Manager and then run *Fetch campaigns* to refresh the stage.
- Archiving a campaign group archives its campaigns on LinkedIn as well,
  except the ones still in Draft, which LinkedIn leaves untouched. Odoo does
  not know about any of it until you run *Fetch campaigns*, so run it
  afterwards to refresh them, and archive the draft campaigns one by one if
  you want them archived too.
- Deleting the campaign in Odoo does not do anything on LinkedIn: the
  campaign keeps running there and the next *Fetch campaigns* brings it
  back. Use *Archive in LinkedIn* to actually end it.
