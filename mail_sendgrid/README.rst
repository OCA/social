.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

==================================
SendGrid Mail Sending and Tracking
==================================

This module integrates
`SendGrid <https://sendgrid.com/>`_ with Odoo. It can send transactional emails
through SendGrid, using templates defined on the
`SendGrid web interface <https://sendgrid.com/templates>`_. It also supports
substitution of placeholder variables in these templates. The list of available
templates can be fetched automatically.
E-mails sent through SendGrid will be tracked using Sendgrid Webhook Events.

Installation
============
You need to install python-sendgrid v3 API in order to install the module.

If you're using a multi-database installation (with or without dbfilter option)
where /web/databse/selector returns a list of more than one database, then
you need to add ``mail_sendgrid`` addon to wide load addons list
(by default, only ``web`` addon), setting ``--load`` option.
For example, ``--load=web,mail_tracking,mail_sendgrid``

Configuration
=============

You can add the following system parameters to configure the usage of SendGrid:

* ``mail_sendgrid.substitution_prefix`` Any symbol or character used as a 
  prefix for `SendGrid Substitution Tags <https://sendgrid.com/docs/API_Reference/SMTP_API/substitution_tags.html>`_.
  ``{`` is used by default.
* ``mail_sendgrid.substitution_suffix`` Any symbol or character used as a 
  suffix for SendGrid Substitution Tags.
  ``}`` is used by default.
* ``mail_sendgrid.send_method`` Use value 'sendgrid' to override the traditional SMTP server used to send e-mails with sendgrid.
  By default, SendGrid will co-exist with traditional system
  (two buttons for sending either normally or with SendGrid).

In order to use this module, the following variables have to be defined in the
server command-line options (or in a configuration file):

- ``sendgrid_api_key`` A valid API key obtained from the
  SendGrid web interface <https://app.sendgrid.com/settings/api_keys> with
  full access for the ``Mail Send`` permission and read access for the
  ``Template Engine`` permission.

Optionally, the following configuration variables can be set as well:

- ``sendgrid_test_address`` Destination email address for testing purposes.
  You can use ``odoo@sink.sendgrid.net``, which is an address that
  will simply receive and discard all incoming email.

For tracking events to work, make sure you configure your Sendgrid Account with the correct Event Notification Url.
You can do it under 'Settings -> Mail Settings -> Event Notification '.
Set the URL to ``https://<your_domain>/mail/tracking/sendgrid/<your_database>``

Replace '<your_domain>' with your Odoo install domain name
and '<your_database>' with your database name.

Usage
=====

If you designed templates in Sendgrid that you wan't to use with Odoo:
    * Go to 'Settings -> Email -> SendGrid Templates'
    * Create a new Template
    * Click the "Update" button : this will automatically import all your templates

In e-mail templates 'Settings -> Email -> Templates', you can attach a SendGrid template for any language.
You can substitute Sendgrid keywords with placeholders or static text like in the body of the e-mail.
The preview wizard now renders your e-mail with the SendGrid template applied.

From e-mails, use the "Send (SendGrid)" button to send the e-mail using Sendgrid.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/205/10.0

Known issues / Roadmap
======================

* Extend the features from SendGrid

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

* Sengrid logo: `SVG Icon <http://seeklogo.com/vector-logo/289294/sendgrid>`_.

Contributors
------------

* Emanuel Cino <ecino@compassion.ch>
* Roman Zoller <rzcomp@gmail.com>

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
