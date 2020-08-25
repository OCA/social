
This module brings Odoo outgoing emails in to strict compliance with RFC-2822
by allowing for a dynamically configured From header.

* Matching mail server: let to choose the proper outgoing mail server for each message depending of the sender domain:

    1) if defined when sending the message use this one
    2) return the one that match with the allowed domain
    3) if not, return the default available one

* When sender domain is not one of the allowed domain, will change the sender domain in the 'Form' of the message with the smpt_form value in the matching mail server

* Will let us to use the config file two values smtp_from and smtp_allowed_domain to be use when not mail server is configured
