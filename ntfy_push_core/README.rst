====================================
ntfy.sh Push Notifications Core
====================================

.. image:: https://img.shields.io/badge/licence-LGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/lgpl-3.0-standalone.html
   :alt: License: LGPL-3

This module integrates Odoo with the **ntfy.sh** protocol to provide real-time,
low-latency, and battery-efficient push notifications. It is designed as a
privacy-first alternative to proprietary push services.

.. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! Developed by nurefexc (https://nurefexc.com)                       !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Key Features
============

* **Zero-Configuration for Users**: Subscription URLs are automatically generated
  when a user switches their notification preference to 'ntfy'.
* **Asynchronous Processing**: Notifications are handled via an internal queue
  and processed in the background to ensure a snappy UI experience.
* **Branded Notifications**: Push messages include the developer's branding (nurefexc)
  and support Markdown formatting.
* **Smart Priority**: All notifications are delivered with **High Priority** to
  ensure they bypass system battery optimizations.
* **Deep Linking**: One-tap access from the notification directly to the Odoo record.
* **Integrated Settings**: Server configuration is seamlessly integrated into the
  Odoo **Discuss** settings.

Configuration
=============

1. Navigate to **Settings > General Settings**.
2. Locate the **Discuss** section.
3. Under **ntfy.sh Push Notifications**, set your **ntfy Server URL** (default is ``https://ntfy.sh``).
4. Ensure the scheduled action **"ntfy: Notification Queue Worker"** is active.

Usage
=====

1. Go to your **User Preferences** (My Profile).
2. Change the **Notification** field to ``ntfy.sh (Push Notification)``.
3. The **ntfy Subscription** field will appear and automatically populate.
4. Hover over the field to see the setup instructions in the tooltip.
5. Use the **Refresh icon** next to the URL if you need to rotate your security token.
6. Copy the URL into your ntfy mobile app (Android/iOS).

Technical Notes
===============

* **Model**: ``ntfy.notification.queue`` manages the outgoing message buffer.
* **Security**: Topic IDs are generated using a SHA256 hash of the database UUID
  and user-specific seeds.
* **UI**: Extends ``base.view_users_form_simple_modif`` for a seamless profile experience.

Credits
=======

Authors
-------

* nurefexc <https://nurefexc.com>

Contributors
------------

* nurefexc <https://nurefexc.com>

Maintainers
-----------

This module is maintained by **nurefexc**.

For professional Odoo development and support, visit `nurefexc.com <https://nurefexc.com>`_.