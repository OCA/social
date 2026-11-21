- The messages appear in *Message Import > Received > Received messages* with
  the channel *WhatsApp*, a link to their Discuss chat and the original data of
  Meta. The filter *WhatsApp* shows only them.
- Only the messages sent to the number of a receiving channel are received;
  the other numbers of the gateway keep working as before.
- A message that Meta delivers again (same `wamid`) is received once, and the
  gateway does not post it again in its chat.
- The reactions and the stickers are recorded but not processed. The text of
  the buttons, lists, locations and contacts is kept as the text of the
  message.
- The module sends no message.
