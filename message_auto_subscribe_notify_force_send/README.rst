.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================================
Message Auto Subscribe Notify Force Send
========================================

With this module users assigned to leads, tasks, issues... will receive an
automatic notification in their email address containing the last discussion
message in the thread.

Some instances where this is valuable is when a lead is created from an
incoming email, and a sales manager assigns it to a salesman. This person
will then receive a notification in his mailbox including the details of the
email from the customer.

This feature existed in 8.0, but was removed as of 9.0.

Configuration
=============

In order to work correctly, the model must meet the following conditions:

* Should inherit from 'mail.thread'.
* The field representing the user should have *track_visibility='onchange'*
  in the field definition.


Usage
=====

To use this module, you need to:

#. Start a conversation for an existing record (e.g. Lead, Task..).
#. Assign the record to a user.
#. A email notification is sent to the assigned user containing the last
   conversation message.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/9.0

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

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Lois Rilo <lois.rilo@eficent.com>
* Jordi Ballester <jordi.ballester@eficent.com>

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
