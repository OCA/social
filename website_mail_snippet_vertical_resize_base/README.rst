.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================================
Base for Vertical Resizing of Snippets
======================================

This module extends the functionality of the website mail designer to support
setting a fixed height in pixels to some elements.

Installation
============

This module is a technical dependency for other modules that want to inherit
its features, so you don't need to install this manually unless you want to use
its features directly (maybe by putting the class in a template element).

When installed, any HTML element in the website mail designer that has the
``vertical_resizable`` will have a new option to ask the user to input its
desired height in pixels.

Usage
=====

When any module installs this one, just click on the desired element and choose
the *Change Height* option to use it.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed `feedback
<https://github.com/OCA/
social/issues/new?body=module:%20
website_mail_snippet_vertical_resize_base%0Aversion:%20
8.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Images
------

* FontAwesome: `Icon <http://fontawesome.io/icon/arrows-v/>`_.

Contributors
------------

* Rafael Blasco <rafabn@antiun.com>
* Jairo Llopis <yajo.sk8@gmail.com>

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
