To configure this module you need to:

- Go to Settings > Technical > Auto Subscribe Mute
- Create a new instance or edit an exiting one. The following fields are available:
  - **Name**. The name of the rule.
  - **Model**. Model in which the rule is applied. Only models with a user_id field can be selected.
  - **Users**. List of users which the rule will be applied to. The users in this field will be autosubscribed to the document when they are set in the user_id field but only with the "Muted" subtype, which notifies nothing. Note that this rule will not be applied when the user in the list set itself in the user_id field, as the subscription in this case depends on the creation of the document, not the autosubscription.
  - **Groups**. List of groups which the rule will be applied to. The users that belong to the groups in this field will be autosubscribed to the document when they are set in the user_id field but only with the "Muted" subtype, which notifies nothing. Note that this rule will not be applied when a user in any of the groups in the list set itself in the user_id field, as the subscription in this case depends on the creation of the document, not the autosubscription.
  - **Notes**. Text field.
