.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

==========================================
Custom notification settings for followers
==========================================

In standard Odoo, receiving mail notifications is an all or nothing affair.
This module allows your users to decide per followed record if they want to
receive emails or not. Further, they can choose to receive notifications about
their own messages.

You can also set defaults for this settings on the subtype in question for all
partners or only for employees.

Configuration
=============

When followers open their subscriptions, they will be offered the choice to
override mail settings and to force being notified about their own messages.

You can add defaults per message sub type for this settings in Settings /
Technical / Email / Subtypes. Here, you also have the opportunity to apply
those defaults to existing subscriptions. Note that this overrides all
customizations your users already have done.

Usage
=====

To use this module, for example you need to:

- Go to Sales -> Sales -> Customers
- Go Inside any customer and in the right-botton corner press "Follow" button
- Unfold Following menu and check new functionality with "mail notificacions"


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
    :alt: Try me on Runbot
    :target: https://runbot.odoo-community.org/runbot/205/8.0

For further information, please visit:

* https://www.odoo.com/forum/help-1


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/social/issues/new?body=module:%20mail_follower_custom_notification%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Holger Brunn <hbrunn@therp.nl>

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
