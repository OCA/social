.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================================
Restrict automatic follower subscription
========================================

This module restricts the followers that are added automatically to a record.
For example, if you use the social ERP functions only internally, it makes
sense to filter possible followers for being employees. Otherwise, you'll get
a quite crowded list of partners to choose from.

Configuration
=============

To configure this module, you need to go to `System parameters` and adjust
`mail_restrict_auto_follower.domain` with the domain to apply to the partners
involved.

This will restrict followers globally. If you want to restrict only the
followers for a certain record type (or have different restrictions for
different record types), create a parameter
`mail_restrict_auto_follower.domain.$your_model`.

As an example, you may use `[('user_ids', '!=', False)]` to allow only
partners that are also users to be added automatically as followers. This is
also the default.

Note: This module won't change existing followers!

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0

Bug Tracker
===========


Bugs are tracked on `GitHub Issues <https://github.com/OCA/
social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback `here <https://github.com/OCA/
social/issues/new?body=module:%20
mail_restrict_automatic_follower%0Aversion:%20
8.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Known issues / Roadmap
======================

* Due to a problem in current API with inheritance, maybe some models ignore
  the restriction. In that cases, a glue module depending on this one is needed
  that redeclares the model this way:

.. code-block:: python

   class Model(models.Model):
       _name = 'model'
       _inherit = ['mail.thread', 'model']

* For v9, this should be merged with `mail_restrict_follower_selection`
  module to have one module for both things that can be called
  `mail_restrict_follower`.

Credits
=======

This module has been inspired on `mail_restrict_follower_selection` module
by Holger Brunn.

Contributors
------------

* Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>

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
