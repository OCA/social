This module provides a generic wizard to send emails in bulk using a mail
template.

- Select multiple records from any list view.
- Choose a mail template (filtered to the current model).
- Queue emails for all selected records in one operation.

The wizard can be triggered from any model by creating an
`ir.actions.server` record that opens it with the appropriate context.
