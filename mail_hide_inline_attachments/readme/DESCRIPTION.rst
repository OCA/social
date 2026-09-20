This module hides inline images from emails in the attachment list of records that
inherit from ``mail.thread`` and also from the ``attachment_ids`` field of the
``mail.message`` model.

When an email contains embedded (inline) images, they are converted into attachments by
Odoo and become visible both in the email body and in the attachment list of the record
and message. This module filters these inline images so they appear only in the email
body.

Features
--------

- Automatically detects attachments that are referenced inline in message bodies
  through:
  - CID (Content-ID) references in ``<img>`` tags
  - ``data-filename`` attributes in ``<img>`` tags
  - ``/web/image/{id}`` URLs in the ``src`` attribute of ``<img>`` tags
- Filters these attachments from the record's attachment list (via ``mail.thread``)
- Filters these attachments from the ``attachment_ids`` field of ``mail.message``
- Images remain visible in the email body
- Works with all models that inherit from ``mail.thread``

How it works
------------

The module intercepts attachment processing at two points:

1. **During message creation** (``mail.thread._message_post_process_attachments``):
   Inline attachments are unlinked from the record (``res_model`` and ``res_id`` are
   cleared), but remain linked to the message.
2. **During message formatting** (``mail.message._message_format``): Inline attachments
   are filtered from the attachment list returned to the web client.

