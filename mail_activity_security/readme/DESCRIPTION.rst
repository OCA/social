This module allows you to configure, for each Activity Type, the security
rules that will be checked to executes actions on the activity.

The following actions are configurable independently:

* Mark as done
* Edit
* Cancel

For each action, you can configure the following security levels:

* Creator: The user who created the activity
* User: The user who's assigned to the activity
* Anyone: Any user with write access to the activity (Odoo default)

These levels are nested. For example, if you set the security level to user,
both the User and the Creator will have access to the action.

Additionally, you can specificy a list of User Groups that will always have
access to all the actions of the activities. This is useful to effectively
give "activity admin access" to the Management groups.
