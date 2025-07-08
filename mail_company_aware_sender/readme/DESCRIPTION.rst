This module allows to send out mails using a company aware email address.
Suppose we have a user Charles the Magnificent with email address
charlemagne@kingdom.fr. However this user works for two companies, one
for the kingdom of France, with email address info@kingdom.fr, and
one for the Roman Empire with email address chancellery@imperiumromanum.org.

Now when sending out mail, we want to make clear from what active company the
mail is sent, but also want to keep the name of the active user in the
email from address, so when sending from the kingdom, the email from will
be charlemagne@kingdom.fr, but when sending from the empire, the email will
be charlemagne@imperiumromanum.org.

Note that after installing this module the system parameter mail.default.from
will no longer be used to set the from address.

This module can also be used to send company aware emails from templates.
For instance with this formula for the email_from field:
{{ object.invoice_user_id.company_aware_email(company=object.company_id) }}
In this example the company defined in the object will be used instead of the current
company.
