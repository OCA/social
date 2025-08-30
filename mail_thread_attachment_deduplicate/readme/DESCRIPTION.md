When this module is installed, when processing attachments in a mail
thread, it will check for duplicates and remove them.

This is typically the case when a customer has inline images in their
emails, like social media links, company logos, etc. If a customer has
10 images in one email, 10 attachments will be created for each message
that is received. After 5 exchanges, that will be 50 attachments, and
potentially relevant ones might be lost in the noise.

Unfortunately, it is not possible to know which attachments are actually
relevant, so this module simply checks for exact duplicates (by
checksum) and removes them. As a result, after install of this module,
the attachments will stay at 10, and only new content will be added.
