Incoming Instagram Direct Messages appear as Discuss channels of type
`gateway`. The sender is a `mail.guest` until a user promotes them to a
partner from the followers menu.

Replies typed in that Discuss channel are delivered as Instagram DMs
(text and supported attachments). Messages the professional account
sends from the Instagram app are not duplicated into the channel unless
**Show Own Messages** is enabled on the gateway. When that setting is
on, those Instagram-app messages appear in the customer's gateway
channel, authored as **Webhook User**.

Shares, story mentions and reels arrive as links in the message body,
not as downloaded files. Images, videos, audio and files are downloaded
and attached to the Discuss message.

Outbound attachments from Discuss are sent as Instagram media when the
filename (or, if the suffix is not recognised, the stored mimetype)
matches Meta's Send Messages formats: png and jpeg images (8 MB);
aac, m4a and wav audio (25 MB); mp4, ogg, ogv, avi, mov and webm video
(25 MB); pdf files (25 MB). Unsupported types, URL attachments, and
files over those limits are rejected before any Graph request. Plaintext
longer than 1000 UTF-8 bytes (Meta's Send Messages cap, not a character
count) is also rejected before any Graph request. A message can be
media-only (no text) or text-only.
