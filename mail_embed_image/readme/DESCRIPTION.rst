This module finds images attached to outgoing emails and replaces their urls
with cids. This will avoid rendering issues with some email clients.

It also provides 2 options to embed internal URL images in a mail body:
 - CIDs: add fileparts as CIDs
 - Data URLs: add images as data URLs

This option is configurable in an company settings variables.
