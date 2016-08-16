.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

==============================
Mail tracking for mass mailing
==============================

Links mail statistics objects with mail tracking objects.


Installation
============

This addon will be automatically installed when 'mail_tracking' and
'mass_mailing' are both installed


Usage
=====

From mail statistic object, you can see:
- Email tracking state
- Email related tracking object
- Email related tracking events

From mass mailing contact, you can see:
- Email score, in order to clean up your lists from bad score emails

As a bonus feature, you have a new checkbox 'Avoid resend' in mass mailing,
in order to not send twice the same email to the same recipient. This is very
useful when you want to resend the mass mailing after changing selection
recipients. Notice that recipient selection could be a domain over a model, so
result ids could change over the time. With this flag you can send
the same email several times but only once to each recipient.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Pedro M. Baeza <pedro.baeza@tecnativa.com>
* Antonio Espinosa <antonio.espinosa@tecnativa.com>

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
