First steps
~~~~~~~~~~~

You need to create a WhatsApp Business Account (WABA), a Meta App and define a phone number.
You can follow this `steps <https://developers.facebook.com/micro_site/url/?click_from_context_menu=true&country=ES&destination=https%3A%2F%2Fwww.facebook.com%2Fbusiness%2Fhelp%2F2087193751603668&event_type=click&last_nav_impression_id=0m3TRxrxOlly1eRmB&max_percent_page_viewed=22&max_viewport_height_px=1326&max_viewport_width_px=2560&orig_http_referrer=https%3A%2F%2Fdevelopers.facebook.com%2Fdocs%2Fwhatsapp%2Fcloud-api%2Fget-started-for-bsps%3Flocale%3Den_US&orig_request_uri=https%3A%2F%2Fdevelopers.facebook.com%2Fajax%2Fpagelet%2Fgeneric.php%2FDeveloperNotificationsPayloadPagelet%3Ffb_dtsg_ag%3D--sanitized--%26data%3D%257B%2522businessUserID%2522%253Anull%252C%2522cursor%2522%253Anull%252C%2522length%2522%253A15%252C%2522clientRequestID%2522%253A%2522js_k6%2522%257D%26__usid%3D6-Trd7hi4itpm%253APrd7ifiub2tvy%253A0-Ard7g9twdm0p1-RV%253D6%253AF%253D%26locale%3Den_US%26jazoest%3D24920&region=emea&scrolled=false&session_id=1jLoVJNU6iVMaw3ml&site=developers>`_.

If you create a test Business Account, passwords will change every 24 hours.

In order to make the webhook accessible, the system must be public.

Configure the gateway
~~~~~~~~~~~~~~~~~~~~~

Once you have created the Meta App, you need to add the gateway and webhook.
In order to make it you must follow this steps:

*  Access `Settings > Emails > Mail Gateway`
*  Create a Gateway of type `WhatsApp`

  *  Use the Meta App authentication key as `Token` field
  *  Use the Meta App Phone Number ID as `Whatsapp from Phone` field
  *  Use the Meta Account Business ID as `Whatsapp account` field (only if you need sync templates)
  *  Write your own `Webhook key`
  *  Use the Application Secret Key on `Whatsapp Security Key`. It will be used in order to validate the data
  *  Press the `Integrate Webhook Key`. In this case, it will not integrate it, we need to make it manually
  *  Copy the webhook URL

* Access `Facebook Apps website <https://developers.facebook.com/apps/>`_
* Access your App then `Whatsapp > Configuration`
* Create your webhook using your URL and put the Whatsapp Security Key as validation Key
* Administer the Webhook and activate the messages webhook
