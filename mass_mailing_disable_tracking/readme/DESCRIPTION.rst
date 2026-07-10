This module allows to disable open and link click tracking in mass mailing messages.

Odoo Mass Mailing (aka Email Marketing) includes 2 ways of tracking (spying on, invade the privacy of) the recipients:

1. Tracking the “opening” of the email message by including a 1-pixel transparent GIF image at the bottom of the message, using a URL to the Odoo instance that uniquely identifies that message sent to that recipient.
   As soon as the recipient displays the remote images of the message, their email client downloads the tracking image and the Odoo instance knows that that particular recipient opened that particular message.
2. Tracking the “clicks” on the links included in the message by converting all links of the message to a tracking URL to the Odoo instance.
   As soon as the recipient clicks one of those links, their browser will make a request to the Odoo instance, which will record that click on that particular link for that particular recipient before redirecting the browser to the original link address.

This module allows to disable both of these mechanisms by preventing the original email message to be modified by Odoo to include these tracking mechanisms.

Another issue that link click tracking causes is that recipients are unable to inspect the links: they cannot know on which website they will land before clicking on them.
This, and the fact that they are tracked, can cause some recipients to not click the links, making the mass mailing actually less effective.

Statistics can be useful, but respecting your recipients’ privacy is important.
