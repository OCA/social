.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

================================
Mandrill mail events integration
================================

This module logs Mandrill email messages events.


Configuration
=============

To configure this module, you need to:

* Define an STMP server in Odoo at Settings > Technical > Email > Outgoing Mail Servers
  using Mandrill credentials from Mandrill settings panel (Settings > SMTP & API Credentials)
* Define a webhook in Mandrill settings panel (Settings > Webhooks) with
  several triggers (Message Is Sent, Message Is Delayed, ...) and 'Post to URL'
  like https://your_odoodomain.com/mandrill/event
* Copy Webhook key and paste in your Odoo configuration file, in 'options'
  section, using 'mandrill_webhook_key' variable. This is optional, but
  recommended because it is used to validate Mandrill POST requests


Usage
=====

When any email message is sent via Mandrill SMTP server, Odoo will add
some metadata to email (Odoo DB, Odoo Model and Odoo Model record ID) using an
special SMTP header (X-MC-Metadata). More info at `Mandrill doc: Using Custom Message Metadata <https://mandrill.zendesk.com/hc/en-us/articles/205582417-Using-Custom-Message-Metadata>`_

Then when an event occurs related with that message (sent, open, click, bounce, ...)
Mandrill will trigger webhook configured and Odoo will log the message and the event.

In 'Setting > Technical > Email > Mandrill emails' you can see all messages sent
using Mandrill. When clicking in one of them you'll see message details and events
related with it

In 'Setting > Technical > Email > Mandrill events' you can see all Mandrill events
received

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/8.0

For further information, please visit:

* https://www.odoo.com/forum/help-1


Known issues / Roadmap
======================

* Define actions associated with events like open/click or bounce
  (via configuration or via other addon)
* Create another addon 'mass_mailing_mandrill' (inheriting from mass_mailing
  and this addon) to process bounces like mass_mailing addon does


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/social/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/social/issues/new?body=module:%20mail_mandrill%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Rafael Blasco <rafabn@antiun.com>
* Antonio Espinosa <antonioea@antiun.com>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
