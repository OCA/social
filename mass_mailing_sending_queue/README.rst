.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================
Mass mailing sending queue
==========================

This module adds a queue for generating mail records when mass mailing
'Send to All' button is clicked. This is an additional queue, apart from
the existing one (implemented in addons/mail) for doing the actual sending.


Configuration
=============

There is a system parameter, 'mail.mass_mailing.sending.batch_size'
(default value is 500), to control how many emails are created in each
cron iteration (method 'mail.mass_mailing.sending.cron()').


Usage
=====

Without this module, when 'Send to All' button is clicked at mass mailing form,
all 'mail.mail' and 'mail.mail.statistics' objects are created. This process
might take a long time if the recipient list is 10k+ and the famous
"Take a minute to get a coffee, because it's loading..." text might appear.

With this new queue, mass mailing will appear in 'Sending' state to the user
until all emails are sent or failed. After 'Send to All' button is clicked,
the user will quickly land to the mass mailing form.

In 'Mass mailing' form, a new tab "Sending tasks" has been added where the
user can check the Sent mails history.

In 'Settings > Technical > Email > Mass mailing sending' allowed users can
track all running mass mailing sending objects and see:

* Pending recipients: Number of recipients for which the email is not yet created.
* Start date: Date when user press 'Send to All' button.
* Mails to be sent: number of emails waiting to be sent.
* Sent mails: number of emails successfully sent.
* Failed mails: number of unsent emails due to error.

NOTE: User will not be able to send the same mass mailing again if another
one is ongoing. An UserError exception is raised in this case.

NOTE: If number of recipients are less than 'batch_size / 2', then all
emails are created when 'Send to All' button is clicked (standard way).
Although a sending object is created anyway in order to be consistent.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0


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

* Antonio Espinosa <antonio.espinosa@tecnativa.com>
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
