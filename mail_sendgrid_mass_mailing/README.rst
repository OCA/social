.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

=========================
SendGrid for mass mailing
=========================

Links mass mailing and mail statistics objects with Sendgrid.
Note that the mass mailing campaign will be sent with Sendgrid transactional
e-emails (not to mix up with Sendgrid marketing campaigns)

Installation
============

This addon will be automatically installed when 'mail_sendgrid' and
'mass_mailing' are both installed.

Configuration
=============
None

Usage
=====

From mass mailing, you can use Sendgrid templates.

#. If you select a Sendgrid template, the campaign will be sent through
   Sendgrid. Otherwise it will use what you set in your system preference
   (see module sendgrid).
#. You can force usage of a language for the template.


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10.0

.. repo_id is available in https://github.com/OCA/maintainer-tools/blob/master/tools/repos_with_ids.txt
.. branch is "8.0" for example

Known issues / Roadmap
======================

* Use Sendgrid marketing campaigns API

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

* Emanuel Cino <ecino@compassion.ch>

Do not contact contributors directly about support or help with technical issues.

Funders
-------

The development of this module has been financially supported by:

* Compassion Switzerland

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
