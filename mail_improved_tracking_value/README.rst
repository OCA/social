.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==============================
Tracking value change improved
==============================

This module extends the mail_tracking_value functionality that records
value changes on predefined fields.
It adds support for many2many and one2many fields, which are not handled
well by default.
It also implements a new view (little bit more user friendly than the
existing one) to watch for changes 

Installation
============

To install this module, you need to:

#. Just install the module

Configuration
=============

To configure this module, you need to:

# No configuration is necessary

Usage
=====

To access the new view displaying value changes :

    Settings -> Technical -> Improved tracking values


Known issues / Roadmap
======================

 * Improve rendering of values depending of type using qweb widgets

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/mail_improved_tracking_value/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Thierry Ducrest <thierry.ducrest@camptocamp.com>

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
