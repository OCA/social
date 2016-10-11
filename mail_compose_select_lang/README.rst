Select language in mail compose window
======================================

This module allows to select the language for the mail content directly in
the mail compose window.

Usage
=====

By default, mail compose window will use corresponding language for showing the
contents, but you will be able to select another language from the dropdown
box "Force language" in the bottom right part.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10.0

Known issues / Roadmap
======================

* Translating attachments is no longer supported as the mechanism for report
  translation has changed. Every report template is translated by a rebrowse
  in the template itself; to make them translatable an inherited view is needed
  for *every* report.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/server-tools/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/server-tools/issues/new?body=module:%20mail_compose_select_lang%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>

Icon
----

* Original icons from Odoo source code.

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
