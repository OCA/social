Configuration
=============

This module does not require additional configuration. It works automatically after
installation.

Inline attachment detection
----------------------------

The module detects inline attachments through three methods:

1. **CID (Content-ID)**: When an ``<img>`` tag has ``src="cid:xxx"``, the attachment with
   that CID is considered inline
2. **data-filename**: When an ``<img>`` tag has the ``data-filename="filename"`` attribute,
   the attachment with that name is considered inline
3. **URL /web/image/{id}**: When an ``<img>`` tag has ``src="/web/image/123"``, the
   attachment with ID 123 is considered inline

All these methods are automatically checked during message processing.

