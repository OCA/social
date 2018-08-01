==========
Activities
==========

This module backports the activities from 11.0.

Configuration
=============

To configure this module, you need to do the same as in 11.0.

Usage
=====

To use this module, you need to do the same as in 11.0.

Known issues / Roadmap
======================

* The button 'Mark done' that appears for each activity in the chatter
  is not available.

* It is not possible to schedule a next activity based on a given activity.

* In v9 a hook is needed in the method 'send_mail' of the transient
  model 'mail.compose.message'. Otherwise the completion of an activity
  will be notified to external partners. In v10 this feature exists out of
  of the box in Odoo.


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

**This module is a backport from Odoo SA and as such, it is not included in the OCA CLA. That means we do not have a copy of the copyright on it like all other OCA modules.**

* Holger Brunn <hbrunn@therp.nl>

Do not contact contributors directly about help with questions or problems concerning this addon, but use the `community mailing list <mailto:community@mail.odoo.com>`_ or the `appropriate specialized mailinglist <https://odoo-community.org/groups>`_ for help, and the bug tracker linked in `Bug Tracker`_ above for technical issues.

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
