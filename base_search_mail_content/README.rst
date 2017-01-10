.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

========================
Base Search Mail Content
========================

This module adds the capability to find any object (e.g. project issues or
helpdesk ticket) based on the conversation threads associated to them.

This will be useful in models that make intense use of messages,
like project issues or helpdesk tickets.

A project issue or helpdesk ticket can contain tens of mails or notes
associated, based on the feedback that the person responsible for the ticket
maintains, including conversations with the person that raised the issue.

A user may often want to find issues or tickets, based on the past
conversations that were recorded, as much as he/she needs to search
in their mail for past conversations.

This module will add dynamically a field 'message_content' to the search view of
any model that inherits from the mail.thread.

The current search capabilities include searching into the subject, body,
email from, reply to and record name.

Installation
============

This module depends on the module 'base_search_fuzzy' to ensure that
searches on emails are based on indexes. Please read carefully the install
instructions:
https://github.com/OCA/server-tools/blob/9.0/base_search_fuzzy/README.rst

This module installs by default the indexes that are required to
perform the searches on mail messages.

Usage
=====

Go to any model that contains a chatter (e.g. Partners, Leads, ...). Search
for content in field 'Message Content'.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/server-tools/9.0

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

* Jordi Ballester Alomar <jordi.ballester@eficent.com>
* Serpent Consulting Services Pvt. Ltd. <support@serpentcs.com>
* Lois Rilo Antelo <lois.rilo@eficent.com>
* Aaron Henriquez <ahenriquez@eficent.com>


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
