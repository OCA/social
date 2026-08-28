- Outbound attachments / media upload.
- Quick replies, icebreakers and the persistent menu.
- HUMAN_AGENT tagging to reply after the 24-hour window: send
  `messaging_type=MESSAGE_TAG` with `tag=HUMAN_AGENT`. Meta documents
  this on the Page Messages API; only `HUMAN_AGENT` is available for
  Instagram Messaging, and the message may be sent within 7 days of the
  customer's last message. Not implemented in 1.0.
- Message reactions, read receipts, and the standby / handover protocol.
- Facebook-Login Instagram (`graph.facebook.com`).
