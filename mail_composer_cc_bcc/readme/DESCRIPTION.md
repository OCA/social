Odoo native does not support defining a Cc field in the Mail Composer by
default; instead, it only has a unique Recipients fields, which is
confusing for a lot of end users.

This module allows to properly separate To:, Cc:, and Bcc: fields in the
Mail Composer.

From Odoo 17.0, this module sends one mail per recipient and keeps same all headers (To, Cc, Bcc) in all emails

## Features

- Add Cc and Bcc fields to company form to use them as default in mail
  composer form.
- Add Bcc field to mail template form. Use Cc and Bcc fields to lookup
  partners by email then add them to corresponding fields in mail
  composer form.
