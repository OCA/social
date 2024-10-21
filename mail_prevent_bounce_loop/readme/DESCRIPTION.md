This module helps to prevent infinite loop between odoo and
autoresponder, which is currently raised in [here](<https://github.com/odoo/odoo/issues/132666>)
- Case 1: odoo sends an invoice email to customer mail address, autoresponder sends auto-reply mail (without enough information for
odoo to detect it as an auto-reply: headers [-loop-detection-bounce-email@/-loop-detection-bounce-email](https://github.com/odoo/odoo/blob/9be0c5348bfeb338bcba95b2a9c01e0d7dd14306/addons/mail/models/mail_thread.py#L1373)). Odoo receives and
send another one, resulting ping-pong situation.
- Case 2: a cron, Notification: Send scheduled
message notifications. When odoo receives automatic reply, the cron
(running by default every hour) sends notifications to all involved
followers of the mail, which then leads to the above issue

Users can avoid the issue by disabling bounce mail at partner level.
