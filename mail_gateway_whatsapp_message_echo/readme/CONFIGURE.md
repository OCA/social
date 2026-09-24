Meta only pushes those messages when the phone number is registered in
coexistence mode, that is, shared between the Cloud API and the WhatsApp
Business app.

- Access [Facebook Apps website](https://developers.facebook.com/apps/)
- Access your App then Whatsapp \> Configuration
- Administer the Webhook and activate the `smb_message_echoes` field, next to
  the `messages` one you already use for the gateway

Echoes are only recorded, they are never sent back to the customer.
