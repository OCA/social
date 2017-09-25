.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

=======================
 Mail split by partner
=======================

This module was written to allow you to choose how the mail was sent to multiple people. The default behavior of Odoo will send one mail for each recipients. The objective of this module would be to allow configuring if the native behavior should be applied or if only one email should be sent to all recipients (convenient to know who else has received the email).

Configuration
=============

* To configure this module, you need to go to `System parameters` and adjust  `default_mail_split_by_partner_conf` as default option when you send mail (`split, merge`).


Usage
=====

To use this module, you need to:

* Go to email template, select `split`,  `merge`, or `default` in the field `Split mail by recipient partner`. If choose `default`, the module will get the value defined on a config parameter `default_mail_split_by_partner_conf`.
* When create mail_message in a thread, the module will use `default` to send mail to followers.

Example, when you choose `split`, it will send one mail for each recipients as default.

Note: Field `Split mail by recipient partner` is available in mail.template and mail.mail so you can check how this email has been processed.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10.0

For further information, please visit:

* https://www.odoo.com/forum/help-1

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/social/issues/new?body=module:%mail_split_by_partner_conf%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Nguyen Tan Phuc <phuc.nt@komit-consulting.com>

Do not contact contributors directly about support or help with technical issues.

Funders
-------

The development of this module has been financially supported by:

* Komit https://komit-consulting.com

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
