This module extends the functionality of mail fetching to support choosing a
mail thread that acts as a mail sink and gathers all mail messages that Odoo
does not know where to put.

Dangling emails are really a problem because if you do not care about them,
SPAM can enter your inbox and keep increasing fetchmail process network quota
because Odoo would gather them every time it runs the fetchmail process.

Before this, your only choice was to create a new record for those unbounded
emails. That could be useful under some circumstances, like creating a
``crm.lead`` for them, but what happens if you do not want to have lots of
spammy leads? Or if you do not need Odoo's CRM at all?

Here we come to the rescue. This simple addons adds almost none dependencies
and allows you to direct those mails somewhere you can handle or ignore at
wish.
