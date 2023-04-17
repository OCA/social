This module aims to facilitate back-and-forth activity assignment between users by
automatically selecting activity creator as the assignee of the followup activity when
using button "Done & schedule next". Use case:

Mitchell Admin assigns activity "to do" to Marc Demo >
Marc Demo clicks "done and schedule next" on the activity >
in new activity form, "assigned to" is set to Mitchell Admin (unless a different default
user is set for the selected activity type).

Furthermore, the module corrects a behavior that can induce user to assigning a new
activity to themselves instead of the previously selected user. Use case:

Mitchell Admin creates a new activity, selects "Marc Demo" as "assigned to", but then
changes activity type.

In standard behavior "assigned to" is reset to "Mitchell Admin";
with this module, the user selection is maintained when changing activity type (unless
a different default user is set for the selected activity type).
