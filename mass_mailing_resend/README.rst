.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

====================
Resend mass mailings
====================

A frequent need for users of mass mailings is to resend one mailing that has
already been sent in the past to new recipients that haven't received yet that
mail. But the problem is to know which are the applicable ones.

Odoo already includes a method in its mass mailing logic that avoids to resend
the same mail 2 times for one mass mailing, and for v9, there was a trick that
allows to modify the state of a mass mailing from kanban view, covering the
need.

But now on v10 both status bar in form view and dragging between states in
kanban are not allowed.

This module introduces a button to restart a mass mailing to draft state,
allowing you to reevaluate the sending domain or list for performing again
the mailing.

Usage
=====

* Go to *Mass mailing > Mailings > Mass Mailings*.
* Click on one record that is done or create a new one and send it.
* You will see a button called "Resend".
* If you click on it, mass mailing will be set to Draft again.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10.0

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Known issues / Roadmap
======================

* Add an indicator / filter for knowing resent mailings.
* Include information on the number of new recipients to be sent on the
  resending (through `get_remaining_recipients` method).


Credits
=======

Contributors
------------

* Tecnativa (https://www.tecnativa.com):
  * Pedro M. Baeza <pedro.baeza@tecnativa.com>

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
