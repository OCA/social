.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

============================
Mail Template Multi Reports
============================

This module adds the option to generate more than one report in an email template.

Also, this module adds the options to attach a report to the email depending on a condition.

Configuration
=============

To configure this module, you need to:

1. Go to Settings -> Technical -> Email -> Templates
2. In the email template form view, go to the Advanced Settings tab.
3. Add extra reports in the Other Reports field.

If the field Condition is filled, then the report will attached depending on
the evaluation of the condition.

Usage
=====

Open a email template wizard and select your template. Your extra reports are added automatically.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/social/8.0

Known issues / Roadmap
======================

The other reports added to the template do not support legacy reports such as rml.
Only qweb reports are available for now.


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

* David Dufresne <david.dufresne@savoirfairelinux.com>


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
