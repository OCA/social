.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

===================================
Default Thread For Unbounded Emails
===================================

This module extends the functionality of mail fetching to support choosing a
mail thread that acts as a mail sink and gathers all mail messages that Odoo
does not know where to put.

Dangling emails are really a problem because if you do not care about them,
SPAM can enter your inbox and keep increasing fetchmail process network quota
because Odoo would gather them every time it runs the fetchmail process.

Before this, your only choice was to create a new record for those unbounded
emails. That could be useful under some circumstances, like creating a
``crm.lead`` for them, but what happens if you do not want to have lots of
spammy leads? Or if you do not need Odoo's CRM at all?

Here we come to the rescue. This simple addons adds almost none dependencies
and allows you to direct those mails somewhere you can handle or ignore at
wish.

Configuration
=============

To configure this module, you need to:

#. Go to *Settings > General Settings > Configure the incoming email gateway*.
#. Create or edit a record.
#. Configure properly.
#. Under *Default mail thread*, choose a model and record.

   Tip: if you do not know what to choose, we suggest you to use a mail
   channel.

Usage
=====

To use this module, you need to:

#. Subscribe to the thread you chose as the *Default mail thread*.
#. You will be notified when a new unbound email lands in that thread.
#. Do what you want with it.

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

* Jairo Llopis <jairo.llopis@tecnativa.com>

Funders
-------

The development of this module has been financially supported by:

* `Tecnativa <https://www.tecnativa.com>`_.

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
