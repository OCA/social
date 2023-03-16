To create new rule:

#. Go to *Mail Template Rule*, Settings > Technical
#. Create new rule:

   - **Name** - Name of your rule
   - **Model** - Model to which rule applies, and domain filter for *mail template*
   - **Template** - Mail Template that will apply for that rule
   - **Context Flag** - Context value that can be used with a specific key *force_mail_template*
   - **Company** - If model has *company_id* field, the rule will only apply to objects from the selected company
   - **Field Expression** - Specific domain that must be met on the object on which the composer is triggered in order for the rule to be applied
   - **Sequence** - Specifies the order of the rules
