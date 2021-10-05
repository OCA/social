[![Runbot Status](https://runbot.odoo-community.org/runbot/badge/flat/205/14.0.svg)](https://runbot.odoo-community.org/runbot/repo/github-com-oca-social-205)
[![Build Status](https://travis-ci.com/OCA/social.svg?branch=14.0)](https://travis-ci.com/OCA/social)
[![codecov](https://codecov.io/gh/OCA/social/branch/14.0/graph/badge.svg)](https://codecov.io/gh/OCA/social)
[![Translation Status](https://translation.odoo-community.org/widgets/social-14-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/social-14-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# social

Addons concerning Odoo's social ERP features and messaging in general.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[base_search_mail_content](base_search_mail_content/) | 14.0.1.0.0 |  | Base Search Mail Content
[email_template_qweb](email_template_qweb/) | 14.0.1.0.0 |  | Use the QWeb templating mechanism for emails
[mail_allow_portal_internal_note](mail_allow_portal_internal_note/) | 14.0.1.0.0 |  | Portal users can access internal messages related to own or other companies
[mail_attach_existing_attachment](mail_attach_existing_attachment/) | 14.0.1.0.0 |  | Adding attachment on the object by sending this one
[mail_autosubscribe](mail_autosubscribe/) | 14.0.1.0.0 |  | Automatically subscribe partners to its company's business documents
[mail_debrand](mail_debrand/) | 14.0.2.0.2 | [![pedrobaeza](https://github.com/pedrobaeza.png?size=30px)](https://github.com/pedrobaeza) [![joao-p-marques](https://github.com/joao-p-marques.png?size=30px)](https://github.com/joao-p-marques) | Remove Odoo branding in sent emails Removes anchor <a href odoo.com togheder with it's parent ( for powerd by) form all the templates removes any 'odoo' that are in tempalte texts > 20characters
[mail_inline_css](mail_inline_css/) | 14.0.1.0.0 |  | Convert style tags in inline style in your mails
[mail_layout_preview](mail_layout_preview/) | 14.0.1.0.0 |  | Preview email templates in the browser
[mail_notification_custom_subject](mail_notification_custom_subject/) | 14.0.1.0.0 | [![joao-p-marques](https://github.com/joao-p-marques.png?size=30px)](https://github.com/joao-p-marques) | Apply a custom subject to mail notifications
[mail_outbound_static](mail_outbound_static/) | 14.0.1.0.0 |  | Allows you to configure the from header for a mail server.
[mail_preview_base](mail_preview_base/) | 14.0.1.0.0 |  | Base to add more previewing options
[mail_restrict_send_button](mail_restrict_send_button/) | 14.0.1.1.0 |  | Security for Send Message Button on Chatter Area
[mail_send_copy](mail_send_copy/) | 14.0.1.0.1 |  | Send to you a copy of each mail sent by Odoo
[mail_tracking](mail_tracking/) | 14.0.1.1.1 |  | Email tracking system for all mails sent
[mail_tracking_mailgun](mail_tracking_mailgun/) | 14.0.1.0.0 |  | Mail tracking and Mailgun webhooks integration
[mail_tracking_mass_mailing](mail_tracking_mass_mailing/) | 14.0.1.0.0 |  | Improve mass mailing email tracking
[mass_mailing_contact_partner](mass_mailing_contact_partner/) | 14.0.1.0.0 | [![ivantodorovich](https://github.com/ivantodorovich.png?size=30px)](https://github.com/ivantodorovich) | Links mailing.contacts with res.partners.
[mass_mailing_custom_unsubscribe](mass_mailing_custom_unsubscribe/) | 14.0.1.0.0 |  | Know and track (un)subscription reasons, GDPR compliant
[mass_mailing_event_registration_exclude](mass_mailing_event_registration_exclude/) | 14.0.1.0.0 |  | Link mass mailing with event for excluding recipients
[mass_mailing_partner](mass_mailing_partner/) | 14.0.1.0.1 |  | Link partners with mass-mailing
[mass_mailing_subscription_date](mass_mailing_subscription_date/) | 14.0.1.0.0 | [![ivantodorovich](https://github.com/ivantodorovich.png?size=30px)](https://github.com/ivantodorovich) | Track contact's subscription date to mailing lists

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to OCA
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----

OCA, or the [Odoo Community Association](http://odoo-community.org/), is a nonprofit
organization whose mission is to support the collaborative development of Odoo features
and promote its widespread use.
