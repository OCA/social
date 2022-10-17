
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/social&target_branch=10.0)
[![Pre-commit Status](https://github.com/OCA/social/actions/workflows/pre-commit.yml/badge.svg?branch=10.0)](https://github.com/OCA/social/actions/workflows/pre-commit.yml?query=branch%3A10.0)
[![Build Status](https://github.com/OCA/social/actions/workflows/test.yml/badge.svg?branch=10.0)](https://github.com/OCA/social/actions/workflows/test.yml?query=branch%3A10.0)
[![codecov](https://codecov.io/gh/OCA/social/branch/10.0/graph/badge.svg)](https://codecov.io/gh/OCA/social)
[![Translation Status](https://translation.odoo-community.org/widgets/social-10-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/social-10-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# Social addons for Odoo

Addons concerning Odoo's social ERP features and messaging in general.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[base_search_mail_content](base_search_mail_content/) | 10.0.1.0.0 |  | Base Search Mail Content
[bus_presence_override](bus_presence_override/) | 10.0.1.0.0 |  | Adds user-defined im status (online, away, offline).
[email_template_qweb](email_template_qweb/) | 10.0.1.0.1 |  | Use the QWeb templating mechanism for emails
[mail_as_letter](mail_as_letter/) | 10.0.1.0.1 |  | This module allows to download a mail message as a pdf letter.
[mail_attach_existing_attachment](mail_attach_existing_attachment/) | 10.0.1.0.1 |  | Adding attachment on the object by sending this one
[mail_check_mailbox_size](mail_check_mailbox_size/) | 10.0.1.0.0 | [![eLBati](https://github.com/eLBati.png?size=30px)](https://github.com/eLBati) | Send an email summarizing the current space used by a mailbox
[mail_debrand](mail_debrand/) | 10.0.1.0.1 |  | Remove Odoo branding in sent emails
[mail_digest](mail_digest/) | 10.0.1.0.2 |  | Basic digest mail handling.
[mail_drop_target](mail_drop_target/) | 10.0.1.0.1 |  | Attach emails to Odoo by dragging them from your desktop
[mail_embed_image](mail_embed_image/) | 10.0.1.0.1 |  | Replace img.src's which start with http with inline cids
[mail_follower_custom_notification](mail_follower_custom_notification/) | 10.0.1.0.1 |  | Let followers choose if they want to receive email notifications for a given subscription
[mail_footer_notified_partner](mail_footer_notified_partner/) | 10.0.1.0.2 |  | This module adds the list of notified partners in the footer of notification e-mails sent by Odoo.
[mail_force_queue](mail_force_queue/) | 10.0.0.2.0 |  | Force outgoing emails to be queued
[mail_forward](mail_forward/) | 10.0.1.0.0 |  | Add option to forward messages
[mail_full_expand](mail_full_expand/) | 10.0.1.0.1 |  | Expand mail in a big window
[mail_improved_tracking_value](mail_improved_tracking_value/) | 10.0.1.0.1 |  | Improves tracking changed values for certain type of fields.Adds a user-friendly view to consult them.
[mail_inline_css](mail_inline_css/) | 10.0.1.0.1 |  | Convert style tags in inline style in your mails
[mail_notify_bounce](mail_notify_bounce/) | 10.0.1.0.2 |  | Notify bounce emails to preconfigured addresses
[mail_optional_autofollow](mail_optional_autofollow/) | 10.0.1.0.1 |  | Choose if you want to automatically add new recipients as followers on mail.compose.message
[mail_optional_follower_notification](mail_optional_follower_notification/) | 10.0.1.0.2 |  | Choose if you want to automatically notify followers on mail.compose.message
[mail_outbound_static](mail_outbound_static/) | 10.0.1.0.0 |  | Allows you to configure the from header for a mail server.
[mail_restrict_follower_selection](mail_restrict_follower_selection/) | 10.0.1.0.1 |  | Define a domain from which followers can be selected
[mail_sendgrid](mail_sendgrid/) | 10.0.1.0.3 |  | SendGrid
[mail_sendgrid_mass_mailing](mail_sendgrid_mass_mailing/) | 10.0.1.0.2 |  | Mass Mailing with SendGrid
[mail_tracking](mail_tracking/) | 10.0.1.1.2 |  | Email tracking system for all mails sent
[mail_tracking_mailgun](mail_tracking_mailgun/) | 10.0.1.2.2 |  | Mail tracking and Mailgun webhooks integration
[mail_tracking_mass_mailing](mail_tracking_mass_mailing/) | 10.0.1.0.1 |  | Improve mass mailing email tracking
[mass_mailing_custom_unsubscribe](mass_mailing_custom_unsubscribe/) | 10.0.2.0.1 |  | Know and track (un)subscription reasons, GDPR compliant
[mass_mailing_event](mass_mailing_event/) | 10.0.1.0.1 |  | Link mass mailing with event for excluding recipients
[mass_mailing_list_dynamic](mass_mailing_list_dynamic/) | 10.0.1.2.0 |  | Mass mailing lists that get autopopulated
[mass_mailing_partner](mass_mailing_partner/) | 10.0.1.0.4 |  | Link partners with mass-mailing
[mass_mailing_resend](mass_mailing_resend/) | 10.0.1.0.0 |  | Resend mass mailings
[mass_mailing_unique](mass_mailing_unique/) | 10.0.1.0.1 |  | Avoids duplicate mailing lists and contacts
[website_mass_mailing_name](website_mass_mailing_name/) | 10.0.1.0.1 |  | Ask for name when subscribing, and create and/or link partner


Unported addons
---------------
addon | version | maintainers | summary
--- | --- | --- | ---
[mail_compose_select_lang](mail_compose_select_lang/) | 8.0.1.0.0 (unported) |  | Select language in mail compose window

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to Odoo Community Association (OCA)
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----
OCA, or the [Odoo Community Association](http://odoo-community.org/), is a nonprofit
organization whose mission is to support the collaborative development of Odoo features
and promote its widespread use.
