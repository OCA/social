.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
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

Usage
=====

From mass mailing, you can use Sendgrid templates.

- If you select a Sendgrid template, the campaign will be sent through
  Sendgrid. Otherwise it will use what you set in your system preference
  (see module sendgrid).
- You can force usage of a language for the template.

Known issues / Roadmap
======================

* Use Sendgrid marketing campaigns API

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/social/issues/new?body=module:%20mail_sendgrid_mass_mailing%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Emanuel Cino <ecino@compassion.ch>

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
