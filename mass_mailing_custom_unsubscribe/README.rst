.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================================================
Customizable unsubscription process on mass mailing emails
==========================================================

This addon extends the unsubscription form to let you:

- Choose which mailing lists are not cross-unsubscriptable when unsubscribing
  from a different one.
- Know why and when a contact has been subscribed or unsubscribed from a
  mass mailing.
- Provide proof on why you are sending mass mailings to a given contact, as
  required by the GDPR in Europe.

Configuration
=============

Unsubscription Reasons
----------------------

You can customize what reasons will be displayed to your unsubscriptors when
they are going to unsubscribe. To do it:

#. Go to *Marketing > Configuration > Unsubscription Reasons*.
#. Create / edit / remove / sort as usual.
#. If *Details required* is enabled, they will have to fill a text area to
   continue.

Usage
=====

Once configured:

#. Go to *Mass Mailing > Mailings > Mass Mailings > Create*.
#. Edit your mass mailing at wish, but remember to add a snippet from
   *Footers*, so people have an *Unsubscribe* link.
#. Send it.
#. If somebody gets unsubscribed, you will see logs about that under
   *Mass Mailing > Mailings > Unsubscriptions*.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/9.0

Known issues / Roadmap
======================

* This module adds a security hash for mass mailing unsubscription URLs, which
  disables insecure URLs from mass mailing messages sent before its
  installation. This can be a problem, but anyway you'd get that problem in
  Odoo 11.0, so at least this addon will be forward-compatible with it.
* This module replaces AJAX submission core implementation from the mailing
  list management form, because it is impossible to extend it. When
  https://github.com/odoo/odoo/pull/14386 gets merged (which upstreams most
  needed changes), this addon will need a refactoring (mostly removing
  duplicated functionality and depending on it instead of replacing it). In the
  mean time, there is a little chance that this introduces some
  incompatibilities with other addons that depend on ``website_mass_mailing``.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Rafael Blasco <rafael.blasco@tecnativa.com>
* Antonio Espinosa <antonio.espinosa@tecnativa.com>
* Jairo Llopis <jairo.llopis@tecnativa.com>

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
