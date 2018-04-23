.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============
Message Edit
============

This module extends the functionality of mail. You can edit message/messages
and move them to any model.

Configuration
=============

To configure this module:

* Activate the 'Move mail message' or 'Edit mail message' permissions for a
  user (the admin user has these rights by default)
* Objects that users are allowed to move messages to, can be
  configured in Settings - Technical - Database structure -
  Referenceable objects.

Usage
=====

To use this module, you need to:

* Go to *Message* *Chatter* in any model, click the Edit (pen) Icon to open up
  the 'Edit or Move' wizard.
* To edit, edit the Mail as necessary and click Save.
* To move, select the destination object and click Save.

Known issues / Roadmap
======================
* Does not reload after edit on messaging views. For this we needed to call
  controller.reload(), a way to this would be to inherit the ActionManager and
  call it from there.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/ social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and
welcomed feedback `here <https://github.com/OCA/
social/issues/new?body=module:%20 mail_edit%0Aversion:%20
8.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`__.


Credits
=======

Images
------

* PICOL Icon Generator `here <http://picol.org/picol_icon_generator>`__.

Contributors
------------

* Dan Kiplangat <dan@sunflowerweb.nl>
* Tom Blauwendraat <tom@sunflowerweb.nl>
* George Daramouskas <gdaramouskas@therp.nl>
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
