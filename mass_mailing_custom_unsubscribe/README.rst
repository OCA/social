.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

==========================================================
Customizable unsubscription process on mass mailing emails
==========================================================

With this module you can set a custom unsubscribe link appended at the bottom
of mass mailing emails.

It also displays a beautiful and simple unsubscription form when somebody
unsubscribes, to let you know why and let the user unsubscribe form another
mailing lists at the same time; and then displays a beautiful and customizable
goodbye message.

Configuration
=============

Unsubscription Message In Mail Footer
-------------------------------------

To configure unsubscribe label go to *Settings > Technical > Parameters >
System parameters* and add a ``mass_mailing.unsubscribe.label`` parameter
with HTML to set at the bottom of mass emailing emails. Including ``%(url)s``
variable where unsubscribe link.

For example::

    <small>You can unsubscribe <a href="%(url)s">here</a></small>

Additionally, you can disable this link if you set this parameter to ``False``.

If this parameter (``mass_mailing.unsubscribe.label``) does not exist, the
default 'Click to unsubscribe' link will appear, with the advantage that it is
translatable via *Settings > Translations > Application Terms > Translated
terms*.

Unsubscription Reasons
----------------------

You can customize what reasons will be displayed to your unsubscriptors when
they are going to unsubscribe. To do it:

#. Go to *Marketing > Configuration > Unsubscription Reasons*.
#. Create / edit / remove / sort as usual.
#. If *Details required* is enabled, they will have to fill a text area to
   continue.

Unsubscription Goodbye Message
------------------------------

Your unsubscriptors will receive a beautier goodbye page. You can customize it
with these links **after installing the module**:

* `Unsubscription successful </page/mass_mailing_custom_unsubscribe.successs>`_.
* `Unsubscription failed </page/mass_mailing_custom_unsubscribe.failure>`_.

Usage
=====

Once configured, just send mass mailings as usual.

If somebody gets unsubscribed, you will see logs about that under
*Marketing > Mass Mailing > Unsubscriptions*.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0

Known issues / Roadmap
======================

* This needs tests.
* This custom HTML is not translatable, so as a suggestion, you can define
  the same text in several languages in several lines.

  For example:

.. code:: html

  <small>[EN] You can unsubscribe <a href="%(url)s">here</a></small><br/>
  <small>[ES] Puedes darte de baja <a href="%(url)s">aquí</a></small>

* If you use the ``website_multi`` module, you will probably find that the
  views are not visible by default.
* This module adds a security hash for mass mailing unsubscription URLs, which
  makes to not work anymore URLs of mass mailing messages sent before its
  installation. If you need backwards compatibility, disable this security
  feature by removing the ``mass_mailing.salt`` system parameter. To avoid
  breaking current installations, you will not get a salt if you are upgrading
  the addon. If you want a salt, create the above system parameter and assign a
  random value to it.
* Security should be patched upstream. Remove security features in the version
  where https://github.com/odoo/odoo/pull/12040 gets merged (if it does).

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/
social/issues/new?body=module:%20
mass_mailing_custom_unsubscribe%0Aversion:%20
8.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Rafael Blasco <rafabn@antiun.com>
* Antonio Espinosa <antonioea@antiun.com>
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
