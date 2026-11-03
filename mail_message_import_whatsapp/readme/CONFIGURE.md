1. Configure a WhatsApp gateway in *Message Import > Configuration > Gateways*
   (administrators only), as explained in `mail_gateway_whatsapp`: the access
   token, the app secret (*Webhook Secret*), the verify token (*Whatsapp
   Security Key*), the webhook key and the *Whatsapp From Phone*. Set the
   webhook in Meta with the webhook URL of the gateway and verify it.
2. In *Message Import > Configuration > Receiving channels*, create a channel:
   - *Channel*: **WhatsApp**.
   - *Gateway*: the WhatsApp gateway.
   - *Meta Phone Number ID*: the identifier of the number in Meta (WhatsApp
     Manager > API setup). The *Whatsapp From Phone* of the gateway is proposed.
   - *Phone Number*: the number the senders write to, to show it.
3. In each sender, tab *Phones and email addresses*, add the phones it sends
   from, with the channel *WhatsApp*. A new phone can also be authorized from
   its first message, in *Message Import > To review > Unknown senders*.

The channel tells what is missing in the gateway, and is *Pending verification*
until the webhook is verified from Meta.
