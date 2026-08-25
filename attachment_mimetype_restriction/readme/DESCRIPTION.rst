This module restricts attachment uploads to an explicit allowlist of MIME types.
Only configured MIME types are accepted; everything else is rejected. Leaving
the allowlist empty disables the restriction and allows all file types.

For incoming emails, the email itself is always accepted, but any attachments
whose MIME type is not in the allowlist are stripped out before the message is
saved. A security notice is then posted on the related record listing the
removed files, so users can see what was filtered.
