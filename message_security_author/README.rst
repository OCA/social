.. image:: https://img.shields.io/badge/license-LGPL--3-blue.png
   :target: https://www.gnu.org/licenses/lgpl
   :alt: License: LGPL-3

=======================
Message Security Author
=======================

Some modules like `mail_tracking` give the users the possibility to access to
the messages by indirect ways. Odoo have not yet regulated what the users can
do to messages because by default in Odoo no users can access to them.

Thus, this `message_security_author` module enters in scene.

This module restricts who can edit/delete messages. Specifically, a message
may be edited or deleted if and only if:

- The user is who created the message previously.
- The user have special permission (is in the group `Mail Message Manager`)

Installation
============

To install this module, simply follow the standard install process.

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/11.0

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

* Odoo Community Association: `Icon <https://odoo-community.org/logo.png>`_.

Contributors
------------

* Miquel Raïch <miquel.raich@eficent.com>

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
