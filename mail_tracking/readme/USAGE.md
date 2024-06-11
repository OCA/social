When user sends a message in mail_thread (chatter), for instance in
partner form, then an email tracking is created for each email
notification. Then a status icon will appear just right to name of
notified partner.

These are all available status icons:

![unknown](../static/src/img/unknown.png) **Unknown**: No email tracking
info available. Maybe this notified partner has 'Receive Inbox
Notifications by Email' == 'Never'

![waiting](../static/src/img/waiting.png) **Waiting**: Waiting to be
sent

![error](../static/src/img/error.png) **Error**: Error while sending

![sent](../static/src/img/sent.png) **Sent**: Sent to SMTP server
configured

![delivered](../static/src/img/delivered.png) **Delivered**: Delivered
to final MX server

![opened](../static/src/img/opened.png) **Opened**: Opened by partner

![cc](../static/src/img/cc.png) **Cc**: It's a Carbon-Copy recipient.
Can't know the status so is 'Unknown'

![noemail](../static/src/img/no_email.png) **No Email**: The partner
doesn't have a defined email

![anonuser](../static/src/img/anon_user.png) **No Partner**: The
recipient doesn't have a defined partner

If you want to see all tracking emails and events you can go to

- Settings \> Technical \> Email \> Tracking emails
- Settings \> Technical \> Email \> Tracking events

When the message generates an 'error' status, it will apear on discuss
'Failed' channel. Any view with chatter can show the failed messages
too.

- Discuss

  ![image](../static/img/failed_message_discuss.png)

- Chatter

  ![image](../static/img/failed_message_widget.png)

You can use "Failed sent messages" filter present in all views to show
records with messages in failed status and that needs an user action.

- Filter

  ![image](../static/img/failed_message_filter.png)
