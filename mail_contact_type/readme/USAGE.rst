In the **Contacts > Configuration > Mailing > Contact type** you can create mail contact type.

A mail contact type is defined by a name that will be displayed in the backoffice
and a code that will be used to find contacts related to this type.

Then, you will need to define the mailing types for contacts. To achieve this
there is a field called **Mail Contact Types** into the contact form view.

Last, to select proper contacts from email template configuration,
you will set the **To (partner)** field using jinja template
like this (assuming `object` as a field `partner_id`):
`${object.partner_id.contact_by_types('your_code1','your_code2')}`
