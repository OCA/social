Roadmap
=====================================

Goals
-----
One of the main goals of the `mail_composer_cc_bcc` module is to make the Mail Composer wizard behave more like a typical Mail Client. This involves addressing the issue where Odoo sends one email per partner by default, causing confusion for end users who may not see all recipients in the email.

Approach
--------
To address the issue of incomplete recipient visibility, the chosen approach is to send a single email with clearly defined headers such as `To:` and `Cc:`. This approach requires full replacement of the `mail.mail:_send` functionality but only when invoked from the Mail Composer.

Limitations
-----------
While the approach of sending a single email with defined headers improves recipient visibility, it introduces two main downsides:

1. Dependency on Upstream Changes: The module needs to track upstream changes in `mail.mail:_send` to ensure compatibility and incorporate any essential fixes. that's the purpose of `test_upstream_file_hash` in tests to monitor changes effectively.

2. Incompatibility with Customized Mail Bodies: Since the module sends the same email to all recipients, it is incompatible with modules that require customization of the mail body per recipient such as `mail_tracking`.

Future Plans
-------------
There are plans to revise the approach during the migration of the module to Odoo 17.0. This revision aims to address the limitations mentioned above and improve overall compatibility with other modules as mail.mail:_send has been made more easy to override