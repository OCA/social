The LinkedIn application.
---------------

- The campaign features (*Create in LinkedIn* and *Fetch campaigns*) require
  an advertising account in the LinkedIn Campaign Manager and the following
  products, which the *Social Media Linkedin* module does not request on its
  own. Ask for them on the *Products* tab of your LinkedIn Developer App,
  following the configuration steps of that module:
  * Advertising API
  * LinkedIn Ad Library

  The access levels of those products are described in the
  [LinkedIn Marketing API documentation](https://learn.microsoft.com/en-us/linkedin/marketing/getting-started).
- The member who authorizes the account must also have a role on that
  advertising account (`ACCOUNT_BILLING_ADMIN`, `ACCOUNT_MANAGER`,
  `CAMPAIGN_MANAGER`, `CREATIVE_MANAGER` or `VIEWER`, the last one read
  only), as listed in the
  [account users documentation](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads/account-structure/create-and-manage-account-users).
  LinkedIn only answers the advertising accounts of the authorized
  member, so without a role the import finds nothing.
- That requirement is unrelated to the formats LinkedIn accepts as an ad: a
  post with several images cannot be sponsored with any product nor with any
  advertising account, because LinkedIn does not turn a multi-image post into
  an ad. See the ROADMAP section about it.

Re-authorize the already associated accounts.
---------------

- Installing this module adds the `r_ads`, `rw_ads` and `r_ads_reporting`
  OAuth scopes to the LinkedIn authorization. The tokens already issued keep
  the scopes they were granted with — refreshing a token does not renegotiate
  them — so every LinkedIn account that was authorized **before** installing
  this module must be re-authorized from the account wizard (*Update
  account* with *Update keys* enabled, which restarts the whole OAuth flow;
  *Update token* only refreshes the current one and keeps its scopes) before
  it can call the Ads API. Installing the module posts that reminder on the
  chatter of every account concerned.
- These scopes belong to the *Advertising API* product, so they are only
  added to the authorization while this module is installed. An account that
  was already granted them keeps asking for them afterwards, because the
  authorization requests what the modules need **and** what the account was
  granted; uninstalling this module takes nothing away from a token LinkedIn
  already issued. To really drop them, empty them from the *Granted Scopes*
  field of the account and authorize it again.
- **LinkedIn does not refuse an authorization that asks for a scope the
  application has no product for: it answers a token without it.** So an
  application without the *Advertising API* product authorizes normally and
  every Ads call is then refused with a `Not enough permissions to access`
  error. The Advertising tab of the account shows which scopes are missing,
  which is the sign the product is not granted on the application rather
  than something to fix in Odoo.

Test and production advertising accounts.
---------------

- The *Environment* of the account maps to the `test` flag
  LinkedIn puts on an advertising account. **LinkedIn sets that flag when the
  advertising account is created and it can never be changed afterwards**, so
  a test advertising account stays a test one for good.
- A test advertising account can only be created through the API, never from
  the Campaign Manager, and **each developer application may only have one**.
  Only `BUSINESS` advertising accounts can be test ones: `ENTERPRISE` cannot.
- Inside a test advertising account the creatives are **never served and are
  automatically rejected** in the review process, and `/adAnalytics` returns
  no data at all. Empty statistics in *Test* are therefore expected, not a
  failure of the module.
- The role requirement above is what makes the list of advertising accounts
  return anything: LinkedIn only answers the advertising accounts the
  authorized member holds a role on.
