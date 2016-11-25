.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

===========================
Mass mailing security group
===========================

This module adds these security features:

* ACL for allowing marketing user group to remove mass.mailing objects
* Security rule to allow marketing user to delete only his unsent mail.mass_mailing objects
* Security rule to allow marketing manager to delete all unsent mail.mass_mailing objects

For sent mail.mass_mailing objects, only a user in Administration / Settings group
could remove them, like standard Odoo defines.


Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/9.0


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and
welcomed feedback.

Credits
=======

Contributors
------------

* Rafael Blasco <rafabn@antiun.com>
* Antonio Espinosa <antonioea@antiun.com>
* Vicent Cubells <vicent.cubells@tecnativa.com>

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
