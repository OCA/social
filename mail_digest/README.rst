.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=========================
Mail digest notifications
=========================

Features
--------

This module allows users/partners to:

* enable "digest mode" in their notification settings
* with digest mode on select a frequency: "daily" or "weekly"
* configure specific rules per message subtype (enabled/disabled)
* globally enable/disable digest based on message's type

to receive or to not receive any email notification for a given subtype.

The preference tab on user's form will look like:

.. image:: ./images/preview.png


Global settings
---------------

By default digest functionality is enabled
for every message type ('email', 'comment', 'notification').
You change this with the config param `mail_digest.enabled_message_types`
whereas you can specify message types separated by comma.


Behavior
--------

When a user with digest mode on is notified with a message or an email
all the messages are collected inside a `mail.digest` container.

A daily cron and a weekly cron will take care
of creating a single email per each digest,
which will be sent as a standard email.

**Rules**

Given that the user has `Notification management = Handle by Emails`...

a message with subtype assigned **will be sent** via digest if:

   * global: `mail_digest_enabled_message_types` param enables the message type
   * user: digest mode is ON for the recipient
   * user: recipient's user has no specific setting for the subtype
   * user: recipient's user has no specific disabling setting for the subtype


a message with subtype assigned **will NOT be sent** via digest if:

  * global: `mail_digest_enabled_message_types` param disables the message type
  * user: digest mode is OFF for the recipient
  * user: recipient's user has disabled the subtype in her/his settings


NOTE: under the hood the digest notification logic excludes followers to be notified,
since you really want to notify only mail.digest's partner.


Known issues / Roadmap
======================

* take full control of message and email template.

Right now the notification message and the digest mail itself is wrapped inside Odoo mail template.
We should be able to customize this easily.

Migrating to v11
----------------

Notification settings, in Odoo core,
`have been moved to user model <https://github.com/odoo/odoo/commit/2950ffaa86ef38263e9a4a59a30d0768f82a61fa#diff-0c15808786b030dc6c62b0b88196afff>`,
and the logic changed a bit.

At the moment there's no staight upgrade provided by this module.
If you need to migrate, keep in mind that:

* `mail.digest` is now tied to user (partner_id -> user_id)
* `notify_email` has been removed so to enable digest mode you have to turn on the new flag `digest_mode`
* `notify_frequency` has been moved to user model and is now called `digest_frequency`
* `partner.notification.conf` became `user.notification.conf`
* `notify_conf_ids` now links the new model `user.notification.conf` and moved to user model


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/social/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing a detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Simone Orsi <simone.orsi@camptocamp.com>


Funders
-------

The development of this module has been financially supported by: `Fluxdock.io <https://fluxdock.io>`_


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
