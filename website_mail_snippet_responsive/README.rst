.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=============================================
Responsive Layout Snippets for Writing Emails
=============================================

This module extends the functionality of the website mail designer to support a
responsive layout and allow you to read those mails comfortably in a mobile
mail client.

Well... actually this is not really responsive. It is pseudo-responsive.
Responsiveness in current mail clients is years behind browsers', so these
templates are very verbose to ensure compatibility in most scenarios. Ideas are
taken from https://css-tricks.com/ideas-behind-responsive-emails/.

Installation
============

This module is prepared to be compatible with module ``website_mail_bg_color``.
If you install it, you will be able to change snippets' background colors, but
it is not required.

Configuration
=============

To change the default background color for buttons:

* Go to *Settings > Configuration > Website Settings > Mail >
  Mail button color*.
* Input `any valid CSS2 color value
  <https://www.w3.org/TR/CSS2/syndata.html#value-def-color>`_.

Usage
=====

To use this module, you need to:

#. Install any module that makes use of the website mail designer, such as
   ``mass_mailing``.
#. Edit an email with the website mail designer.
#. You have a new collection of snippets under *Email Design* section. Use them
   as usual.

If you choose the *Horizontal Separator* snippet, you will be able to set its
height too. For that, you will have to aim carefully to click inside the green
line, and then use the option that will float above it.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0

Known issues / Roadmap
======================

* Snippet is ugly, but that's because mail client HTML engines usually lack
  many of the modern CSS and HTML features. I hope we will be able to improve
  this as mail clients keep improving.
* To set the *Horizontal Separator* height, you have to click inside it, which
  will insert a ``<br type="_moz"/>`` in Firefox, that will make it seem like
  its height is at least like a caret, even if you set a lower value. Do not
  worry, it goes away when you press *Save*.
* Some elements do not render with the proper width in MS Outlook. This should
  be added inside each snippet to make them work::

      <!--[if gte mso]>
          <style type="text/css">
          .fluid { width: 600px !important; }
          </style>
      <![endif]-->

  But right now the view parser eats comments, and if you avoid that then
  CKEditor will eat them, so there's not an easy solution for now.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed `feedback
<https://github.com/OCA/
social/issues/new?body=module:%20
website_mail_snippet_responsive%0Aversion:%20
8.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Daniel Gómez-Zurita <danielgz@antiun.com>
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
