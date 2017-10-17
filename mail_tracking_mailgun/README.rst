.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=========================
Mail tracking for Mailgun
=========================

This module integrates mail_tracking events with Mailgun webhooks.

Mailgun (https://www.mailgun.com/) is a service that provides an e-mail
sending infrastructure through an SMTP server or via API. You can also
query that API for seeing statistics of your sent e-mails, or provide
hooks that processes the status changes in real time, which is the
function used here.

Configuration
=============

You must configure Mailgun webhooks in order to receive mail events:

1. Got a Mailgun account and validate your sending domain.
2. Go to Webhook tab and configure the below URL for each event:

.. code:: html

   https://<your_domain>/mail/tracking/all/<your_database>

Replace '<your_domain>' with your Odoo install domain name
and '<your_database>' with your database name.

In order to validate Mailgun webhooks you have to configure the following system
parameters:

- `mailgun.apikey`: You can find Mailgun api_key in your validated sending
  domain.
- `mailgun.api_url`: It should be fine as it is, but it could change in the
  future.
- `mailgun.validation_key`: If you want to be able to check mail address
  validity you must config this parameter with your account Public Validation
  Key.

Usage
=====

In your mail tracking status screens (explained on module *mail_tracking*), you will
see a more accurate information, like the 'Received' or 'Bounced' status, which are
not usually detected by normal SMTP servers.

It's also possible to make some checks to the partner's email addresses against the Mailgun API:

- Check if the partner's email is in Mailgun's bounced list.
- Check the validity of the partner's mailbox.
- Force the partner's email into Mailgun's bounced list or delete from it.

It's also possible to manually check a message mailgun tracking when the webhook
couldn't be captured. For that, go to that message tracking form, press the
button *Check Mailgun*. It's important to note that tracking events have quite a
short lifespan, so after 24h they won't be recoverable.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/9.0

Known issues / Roadmap
======================

* There's no support for more than one Mailgun mail server.

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

* Mailgun logo: `SVG Icon <http://seeklogo.com/mailgun-logo-273630.html>`_.

Contributors
------------

* Antonio Espinosa <antonio.espinosa@tecnativa.com>
* Carlos Dauden <carlos.dauden@tecnativa.com>
* Pedro M. Baeza <pedro.baeza@tecnativa.com>
* David Vidal <david.vidal@tecnativa.com>
* Rafael Blasco <rafael.blasco@tecnativa.com>

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
