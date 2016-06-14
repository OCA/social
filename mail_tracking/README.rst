.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

=============
Mail tracking
=============

This module shows email notification tracking status for any messages in
mail thread (chatter). Each notified partner will have an intuitive icon just
right to his name.


Installation
============

If you're using a multi-database installation (with or without dbfilter option)
where /web/databse/selector returns a list of more than one database, then
you need to add ``mail_tracking`` addon to wide load addons list
(by default, only ``web`` addon), setting ``--load`` option.
For example, ``--load=web,mail_tracking``


Usage
=====

When user sends a message in mail_thread (chatter), for instance in partner
form, then an email tracking is created for each email notification. Then a
status icon will appear just right to name of notified partner.

These are all available status icons:

.. |sent| image:: mail_tracking/static/src/img/sent.png
   :width: 10px

.. |delivered| image:: mail_tracking/static/src/img/delivered.png
   :width: 15px

.. |opened| image:: mail_tracking/static/src/img/opened.png
   :width: 15px

.. |error| image:: mail_tracking/static/src/img/error.png
   :width: 10px

.. |waiting| image:: mail_tracking/static/src/img/waiting.png
   :width: 10px

.. |unknown| image:: mail_tracking/static/src/img/unknown.png
   :width: 10px

|unknown|  **Unknown**: No email tracking info available. Maybe this notified partner has 'Receive Inbox Notifications by Email' == 'Never'

|waiting|    **Waiting**: Waiting to be sent

|error|    **Error**: Error while sending

|sent|    **Sent**: Sent to SMTP server configured

|delivered|    **Delivered**: Delivered to final MX server

|opened|  **Opened**: Opened by partner


.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0

If you want to see all tracking emails and events you can go to

* Settings > Technical > Email > Tracking emails
* Settings > Technical > Email > Tracking events


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
* Thanks to `LlubNek <https://openclipart.org/user-detail/LlubNek>`_ and `Openclipart
  <https://openclipart.org>`_ for `the icon
  <https://openclipart.org/detail/19342/open-envelope>`_.

Contributors
------------

* Pedro M. Baeza <pedro.baeza@tecnativa.com>
* Antonio Espinosa <antonio.espinosa@tecnativa.com>

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
