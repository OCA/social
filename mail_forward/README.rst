.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

===============
Message forward
===============

This module was written to extend the functionality of mails to support
forwarding them to another contact or database object.

* **To another object of the database:** All its followers are notified
  according to their settings.

* **To other contacts:** They recieve the forwarded message according to the
  usual notification rules of Odoo.

Configuration
=============

When installed, this module allows forwarding to a limited selection of
database models, that will get automatically updated when you install other
modules.

This list can be customized by a user that has *Technical Features* permission.
To do it:

* Go to *Settings > Technical > Database Structure > Referenceable Models*.

* Any model there with *Mail forward target* enabled will appear in the list of
  models that can get forwarded messages.

  * If you want to *remove* a model from the list, it's usually better to just
    *disable* its check box instead of deleting it, because that record might
    be used by other modules.

Usage
=====

To use this module, you need to:

* Go to any view that has a message thread.
* Press *Forward* (the button with a curved arrow pointing to the right).
* Modify the subject if you wish.
* If you want to forward the message to an *object*, choose it from the
  selector.
* If you want to forward the message to some partner(s), add them in the
  selector.
* Modify the message if you want.
* Add attachments if you want.
* If the message contains attachments, you can turn on the *Move attachments*
  option, and those will get attached to the new object.

  You will need to install the *document* module and have at least *User*
  permissions for *Knowledge* to see the effect.

.. info::
    Technical note: Internally, forwarded messages are modified copies of
    original ones, but attachments are references to the exact originals to
    avoid duplicating disk space. Keep that in mind when managing permissions.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0

For further information, please visit:

* https://www.odoo.com/forum/help-1

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/social/issues>`_. In
case of trouble, please check there if your issue has already been reported. If
you spotted it first, help us smashing it by providing a detailed and welcomed
feedback `here
<https://github.com/OCA/social/issues/new?body=module:%20mail_forward%0Aversion:%208.0.7.0.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Jairo Llopis <j.llopis@grupoesoc.es>

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
