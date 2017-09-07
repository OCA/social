.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===============
Mail Inline CSS
===============

When you send HTML emails you can't use style tags but instead you have
to put inline ``style`` attributes on every element. So from this:

.. code:: html

    <html>
    <style type="text/css">
    h1 { border:1px solid black }
    p { color:red;}
    </style>
    <h1 style="font-weight:bolder">Peter</h1>
    <p>Hej</p>
    </html>

You want this:

.. code:: html

    <html>
    <h1 style="font-weight:bolder; border:1px solid black">Peter</h1>
    <p style="color:red">Hej</p>
    </html>

This module use premailer library to do this. 

It parses an HTML page, looks up ``style`` blocks
and parses the CSS. It then uses the ``lxml.html`` parser to modify the
DOM tree of the page accordingly.

Installation
============

To install this module, you need first to install `premailer` python library with:

.. code:: bash

    pip install premailer


Usage
=====

Just use any mail template as Odoo standard feature

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10


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

* David BEAL <david.beal@akretion.com>

Do not contact contributors directly about support or help with technical issues.

Funders
-------

The development of this module has been financially supported by:

* Akretion

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
