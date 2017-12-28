.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

====================
Notify bounce emails
====================

In case of bounced email messages retrieved by fetchmail, sender of original message will be notified. Also, it is possible to configure email addresses to be notified about bounced emails.

Typical use case:

 - User configures a partner with a wrong email address
 - User sends a message to that partner
 - User gets notified about wrong email address

In some cases (see `https://github.com/odoo/odoo/issues/21119
<https://github.com/odoo/odoo/issues/21119>`_.), these messages are silently discarded by odoo, so users don't know about possible failures.
Also, even when bounce messages are correctly fetched by odoo, the sender, or other people, will not be notified.

Configuration
=============

To configure additional recipients of bounced emails, you can open fetchmail server form and fill 'Notify bounce emails to' field

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Icon made by those-icons from https://www.flaticon.com/authors/those-icons

Contributors
------------

* Lorenzo Battistini <lorenzo.battistini@agilebg.com>

Do not contact contributors directly about support or help with technical issues.

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
