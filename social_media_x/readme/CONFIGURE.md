To configure this module, you need to:
---------------
Please note that you must have a developer account.

**Important:** the X API v2 endpoints used by this module require a developer
App **attached to a Project** and a **paid plan** (Pay Per Use, or a legacy
Basic/Pro subscription). Since February 2026 the Free access tier no longer
grants general access to the API, so the account cannot be associated with a
Free-tier App. The association wizard shows this warning, and when X rejects
the request for this reason the module replaces the raw error with a message
pointing to the pricing page. Note that the authorization screen of X is still
shown with a Free-tier App: the rejection only happens afterwards, when the
module reads the authorized user, and the message is then displayed on the
Dashboard. See the ROADMAP section for details.

The steps required for using it are defined below:

- Go to https://developer.twitter.com/en/portal/dashboard
- Create a developer account.
- Once the account is created, go to Projects and APPS -> Default Project and select it.

  ![PROJECT_DEFAULT](../static/img/readme/PROJECT_DEFAULT.png)

- Then scroll to the bottom of the page and press the Edit button.

  ![CONFIGURATION_ACCOUNT](../static/img/readme/CONFIGURATION_ACCOUNT.png)

- Once on the page, in the App Permissions section, select the Read and Write and Direct Messages.

  ![APP_PERMISIONS](../static/img/readme/APP_PERMISIONS.png)

- Go to the App Type section and select Web App, Automated App or Bot.

  ![TYPE_APP](../static/img/readme/TYPE_APP.png)

- Then, in the Callback URI / Redirect URL section, add a new address. Here are the steps to get that URL in Odoo:
   * Go to *Configuration* > *Technical* > System Parameters.
   * Search for web.base.url
   * Copy the base URL and concatenate it with the endpoint.
     Example:
      web.base.url: http://192.168.1.7:8017
      endpoint: /social_x/callback (this value is fixed)
      callback_url: http://192.168.1.7:8017/social_x/callback

- Then go to the Website URL section and add your X profile address.

   Example: https://x.com/AccountTest

  ![CALLBACK_URI_WEBSITE_URL](../static/img/readme/CALLBACK_URI_WEBSITE_URL.png)

- Finally, go to Projects and APPS -> Default Project -> Keys and Tokens,
   press the Regenerate button, and then in the window that appears, confirm
   the generation of the API Key and API Key Secret values.

  ![KEYS_AND_TOKENS](../static/img/readme/KEYS_AND_TOKENS.png)

  ![GENERATE_NEW_KEY_SECRET](../static/img/readme/GENERATE_NEW_KEY_SECRET.png)

Learn more at [X Developer Portal](https://developer.twitter.com)

Registering the API Key and API Key Secret. Integration of a user account.
---------------

- Go to *Social Media* > Configuration > Social medias
- Click on  the *Associate Account* button for the desired social network.

  ![ASSOCIATE_ACCOUNT](../static/img/readme/ASSOCIATE_ACCOUNT.png)
-
- A wizard will open for you to add the API Key and API Key Secret obtained
  from your developer account.

  ![WIZARD_ASSOCIATE_ACCOUNT](../static/img/readme/WIZARD_ASSOCIATE_ACCOUNT.png)

- By clicking the *Associate* button here, you'll be taken to a X authentication page.
  Once you validate your information, you'll be taken to the system and the Dashboard view,
  where you'll see your posts.

  ![AUTHORIZE_ACCOUNT](../static/img/readme/AUTHORIZE_ACCOUNT.png)

- Once you have completed these steps and everything is working correctly,
  you can see your account in *Social Media* > Configuration > Accounts
- After the account is associated, an initial synchronization of its posts
  and statistics is triggered automatically.
- Note that the account credentials (API Key, API Secret and tokens) are
  masked and only visible to administrator users.
- The authorization flow is bound to the session that started it: the request
  token returned by X only works for the user who opened the wizard. A
  callback without a request token, or with the request token of another
  user, is refused with *Invalid X callback: the request token is missing.*
  or *Invalid X request token. Please restart the account association
  process.*
- If the X account is already linked to an account of another Odoo user, the
  association is refused and nothing is overwritten: only the responsible
  user of the account and the *Social Media / Administrator* group can
  relink it.
