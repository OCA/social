.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==========================
Dynamic Mass Mailing Lists
==========================

Without this addon you have to choose between providing a dynamic domain and
letting your mass mailings reach all partners that match it, or being able to
unsubscribe to certain mailing lists while still being subscribed to others.

This addon allows you to create dynamic mailing lists, so you can now benefit
from both things.

Configuration
=============

To create a dynamic mailing list, you need to:

#. Go to *Mass Mailing > Mailings > Mailing Lists* and create one.
#. Check the *Dynamic* box.
#. Choose a *Sync method*:
   - Leave empty to use as a manual mailing list, the normal behavior.
   - *Only add new records* to make sure no records disappear from the list
     when partners stop matching the *Synchronization critera*.
   - *Add and remove records as needed* to make the list be fully synchronized
     with the *Synchronization critera*, even if that means removing contacts
     from it.
#. Define a *Synchronization criteria* that will be used to match the partners
   that should go into the list as contacts. Only partners with emails will
   be selected.

You can also load an existing filter over contacts:

#. Click on "Load filter" button below criteria.
#. Select one of the existing filters.
#. Click on "Load filter" and you will have that filter as criteria.

Usage
=====

#. Go to *Mass Mailing > Mailings > Mass Mailings*, and create one.
#. Select as recipients a mailing list.
#. On "Select mailing lists:", choose one mailing list with dynamic flag
   checked.
#. Before sending the mass mailing, the list will be synced for having latest
   changes.

Usage
=====

When you hit the *Sync now* button or send a mass mailing to this list, its
contacts will be automatically updated.

Pay attention to the messages shown to you that tell you about some non-obvious
behaviour you could experience if you edit manually contacts from a dynamic
list.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10.0

Known issues / Roadmap
======================

* Tests affected by https://github.com/odoo/odoo/issues/20603. Do not run them
  in stateful databases.

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

* Odoo.
* FontAwesome (http://fontawesome.io).

Contributors
------------

* `Tecnativa <https://www.tecnativa.com>`_:
  * Jairo Llopis <jairo.llopis@tecnativa.com>
  * Pedro M. Baeza <pedro.baeza@tecnativa.com>

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
