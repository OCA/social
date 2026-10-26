Usage
=====

After installation, the module works automatically. No additional configuration is
required.

Behavior
--------

When an email is received or sent with inline images:

1. Images are processed normally and appear in the email body
2. Corresponding attachments are created in the system
3. Inline attachments are automatically filtered and do not appear:
   - In the record's attachment list (chatter)
   - In the ``attachment_ids`` field of ``mail.message``
4. Only attachments that are not inline images remain visible in the attachment list

Example
-------

If an email contains:

- 1 inline image (company logo)
- 2 normal attachments (PDF and DOCX)

The result will be:

- The inline image appears only in the email body
- The 2 normal attachments appear in the record's and message's attachment list

