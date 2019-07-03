When user sends a message in mail_thread (chatter), for instance in partner
form, then an email tracking is created for each email notification. Then a
status icon will appear just right to name of notified partner.

These are all available status icons:

.. |sent| image:: mail_tracking/static/src/img/sent.png
   :width: 10px

.. |delivered| image:: mail_tracking/static/src/img/delivered.png
   :width: 15px

.. |opened| image:: mail_tracking/static/src/img/opened.png
   :width: 15px

.. |error| image:: mail_tracking/static/src/img/error.png
   :width: 10px

.. |waiting| image:: mail_tracking/static/src/img/waiting.png
   :width: 10px

.. |unknown| image:: mail_tracking/static/src/img/unknown.png
   :width: 10px

.. |cc| image:: static/src/img/cc.png
   :width: 10px

|unknown|  **Unknown**: No email tracking info available. Maybe this notified partner has 'Receive Inbox Notifications by Email' == 'Never'

|waiting|    **Waiting**: Waiting to be sent

|error|    **Error**: Error while sending

|sent|    **Sent**: Sent to SMTP server configured

|delivered|    **Delivered**: Delivered to final MX server

|opened|  **Opened**: Opened by partner

|cc|  **Cc**: It's a Carbon-Copy recipient. Can't know the status so is 'Unknown'


If you want to see all tracking emails and events you can go to

* Settings > Technical > Email > Tracking emails
* Settings > Technical > Email > Tracking events
