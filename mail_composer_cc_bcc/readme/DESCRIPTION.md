Odoo native does not support defining a Cc field in the Mail Composer by
default; instead, it only has a unique Recipients fields, which is
confusing for a lot of end users.

This module allows to properly separate To:, Cc:, and Bcc: fields in the
Mail Composer.

## Features

- Add Cc and Bcc fields to mail composer form. Send only once to
  multiple email addresses.
- Add Cc and Bcc fields to company form to use them as default in mail
  composer form.
- Add Bcc field to mail template form. Use Cc and Bcc fields to lookup
  partners by email then add them to corresponding fields in mail
  composer form.
