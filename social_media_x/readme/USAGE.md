List of posts generated from Odoo.
---------------

Only posts generated using Odoo are displayed.

- Go to *Social Marketing* > Post

Generate a post.
---------------

This feature acts as a template for generating multiple posts
from a single view, depending on the selected accounts.

- Go to *Social Marketing* > Post > New or Go to *Social Marketing* > Dashboard > Add Post
- Fill in the required fields
  ![CREATE_POST](/social_media_x/static/img/readme/CREATE_POST.png)
- Save
- Click on the *Post* button

Update token, client ID, client Secret and organization data
---------------

- Go to *Social Media* > Configuration > Accounts
- Select the account
- Click on the *Update account* button

  ![BUTTON_UPDATE_ACCOUNT](/social_media_linkedin/static/img/readme/BUTTON_UPDATE_ACCOUNT.png)

- In the wizard that appears, if none of the checkboxes are selected and the
  *Update* button is pressed, the system will update only the organization's data.
- If the *Update keys* checkbox is selected, the current Client ID and Client Secret
  values will be displayed by default. Modify any of these values and authentication
  will be performed again through LinkedIn to update these values and the token.

  ![UPDATE_KEYS](/social_media_linkedin/static/img/readme/UPDATE_KEYS.png)

- Selecting the *Update token* checkbox will update the current token.

  ![UPDATE_TOKEN](/social_media_linkedin/static/img/readme/UPDATE_TOKEN.png)


Archive Account X
----------------------------
- Go to *Social Media* > Configuration > Accounts
- Select the account
- Click on the *Delete account* button

  ![ARCHIVE_ACCOUNT](/social_media_linkedin/static/img/readme/ARCHIVE_ACCOUNT.png)

- Please note that all data associated with this account will be archived.

Enable since
------------------------
- Go to *Social Media* > Configuration > Accounts
- Select the account
- Select *Enable since*
- The *Post since* field is then enabled, allowing you to
  select the post to start the search for in the next post
  retrieval. Note that metrics for older posts will not be updated
  if this option is selected.

  ![ENABLE_SINCE](/social_media_linkedin/static/img/readme/ENABLE_SINCE.png)
