.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

===============================
Link partners with mass-mailing
===============================

This module links mass-mailing contacts with partners.

Features
--------
* When creating or saving a mass-mailing contact, partners are matched through
  email, linking matched partner, or creating a new one if no match and the
  maling list partner mandatory field is checked.
* Mailing contacts smart button in partner form.
* Mass mailing stats smart button in partner form.
* Filter and group by partner in mail statistics tree view


Configuration
=============

At first install, all existing mass mailing contacts are matched against
partners. And also mass mailing statistics are matched using model and res_id.

Usage
=====

In partner view, there is a new action called "Add to mailing list". This
action open a pop-up to select a mailing list. Selected partners will be added
as mailing list contacts.

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

Contributors
------------

* Pedro M. Baeza <pedro.baeza@tecnativa.com>
* Rafael Blasco <rafael.blasco@tecnativa.com>
* Antonio Espinosa <antonio.espinosa@tecnativa.com>
* Javier Iniesta <javieria@antiun.com>
* Jairo Llopis <jairo.llopis@tecnativa.com>
* David Vidal <david.vidal@tecnativa.com>


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
