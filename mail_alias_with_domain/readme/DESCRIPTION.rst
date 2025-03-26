This module adds possibility to process aliases together with domain.

For example, suppose we have 3 companies in odoo.
Each company wants to have an alias where customers can send the bills.
invoice@company1.com
invoice@company2.com
invoice@company3.com

In odoo, aliases are unique, and this module extends this functionality in
such a way that you can have many of the same aliases but with different domains.

Note that when an incoming mail can be linked to an alias with a domain,
this will be the only alias used. However when an incoming mail can be
linked to multiple aliasses that have a domain, it is possible to have
multiple used.

FOR DEVELOPERS

In the default alias system, only the local part of an email address (the part
before the @) is used to link an incoming email to an alias. This happens in the
message_route method of the mail.thread model.

Aliasses in standard Odoo store the alias_name field without domain.

To still be able to use a domain name, we need a trick. What we will do is:

* Replace the alias_name in the user interface with an alias_entry field, where a
  complete email address can be entered.

* If an alias is entered as a complete email address, this will be stored in the
  alias_name as <localpart>__at__<domain>. For instance alex__at__example.com.
  alias_name is therefore changed from a writable field to a stored computed field.

* The computation of alias_domain will be enhanced to take full email addresses into
  account.

* If an incoming mail can be linked to a full email address alias, we will write a
  context key pointing to this alias. The search method of mail.alias will be overriden
  to check for this key, and then not search at all, but just return the alias
  requested.

