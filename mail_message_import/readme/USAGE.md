- *Message Import > Panel* shows a card per receiving channel with what is left
  to review.
- *Message Import > To review > Unknown senders* lists the messages of addresses
  that are not authorized. Select them and press **Assign to a sender**: the
  address can be authorized for the next messages, and the messages are
  processed as a conversation of the sender.
- *Message Import > Received > Conversations* lists the conversations. A
  conversation waiting for more messages can be processed at once with
  **Process now**, and one in error can be processed again with **Retry**.
- *Message Import > To review > Incidents* lists what could not be done, for
  example a conversation that failed every attempt. **Retry** processes it
  again once the cause is solved.

For developers, a channel module:

- adds its value to `mail.message.import.channel.channel_type` and tells the state
  of its channels in `_channel_state()`;
- tells how its addresses are compared in
  `mail.message.import.address._normalize_address()`;
- hands over each message with `mail.message.import.message._receive_message()`.

A module that processes the conversations overrides
`mail.message.import.conversation._process_messages()`, which gets the messages in
chronological order, with their files downloaded and their forwarded emails
unpacked.
