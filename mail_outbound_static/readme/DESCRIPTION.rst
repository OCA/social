This module brings Odoo outbound emails in to strict compliance with RFC-2822
by allowing for a dynamically configured From header, with the sender's e-mail
being appended into the proper Sender header instead. To accomplish this we:

* Add a domain whitelist field in the mail server model. This one represent an
  allowed Domains list separated by commas. If there is not given SMTP server
  it will let us to search the proper mail server to be used to send the messages
  where the message 'From' email domain match with the domain whitelist. If
  there is not mail server that matches then will use the default mail server to
  send the message.

* Add a Email From field that will let us to email from a specific address taking
  into account this conditions:

  1) If the sender domain match with the domain whitelist then the original
     message's 'From' will remain as it is and will not be changed because the
     mail server is able to send in the name of the sender domain.

  2) If the original message's 'From' does not match with the domain whitelist
     then the email From is replaced with the Email From field value.

* Add compatibility to define the smtp information in Odoo config file. Both
  smtp_from and smtp_whitelist_domain values will be used if there is not mail
  server configured in the system.
