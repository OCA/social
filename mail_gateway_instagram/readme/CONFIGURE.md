The connector uses the Instagram API with Instagram Login
(`graph.instagram.com`). Facebook-Login / Page-scoped Instagram is not
supported.

## Meta app

**IMPORTANT — publish the Meta app (Live mode).** Webhook verification
can succeed while the app is still in Development, but Instagram Direct
Messages are **not delivered** to Odoo until the app is **published**
(switched to Live). Without Live mode you will see an integrated
webhook and no inbound POSTs, and no Discuss channels. Do this **before**
expecting real DMs to work. App Review / Advanced Access is also
required for permissions that serve Instagram accounts the app does not
own.

1. Use an Instagram **professional** account (Business or Creator).
2. Create a Meta app at
   [developers.facebook.com/apps](https://developers.facebook.com/apps/)
   and add the **Instagram Login** product.
3. Request `instagram_business_basic` and
   `instagram_business_manage_messages`. Advanced Access is required to
   serve Instagram accounts the app does not own.
4. **Publish the app** (Development → Live). This step is mandatory for
   messaging delivery; skip it and inbound DMs will never arrive.

## Odoo gateway

1. Enable developer mode, then go to Settings > Technical > Email >
   Gateway. (Technical is visible only in the developer mode.)
2. Create a gateway of type **Instagram**.
3. Fill in:
   - **Token**: Instagram user access token (sent as `Authorization: Bearer`).
   - **Webhook Secret**: Meta **app secret** (HMAC key for
     `X-Hub-Signature-256`). Copy it from the Meta app
     Settings > Basic > App Secret.
   - **Instagram Security Key**: a string you choose. You will enter the
     same value in Meta as the webhook **verify token**
     (`hub.verify_token`).
   - **Instagram Account**: professional account IGID used in the send
     URL.
   - **Instagram Version**: Graph API version without the `v` prefix
     (default `26.0`).
   - **Webhook Key**: URL path segment of your choice. It becomes part
     of the webhook URL.
   - **Webhook User**: user that creates inbound messages.
   - **Members**: Discuss users who join new conversations.
4. Save. **Webhook Key** and **Webhook User** must be set or the
   **Integrate Webhook** button stays hidden.
5. Press **Integrate Webhook** on the gateway form (header). The state
   becomes `pending`. Meta's verification GET is only accepted in this
   state.
6. Open the **Instagram configuration** tab on the same form. Copy
   **Webhook URL**. Odoo builds it as
   `https://<your-odoo-host>/gateway/instagram/<webhook_key>/update`.
   You do not get this URL from Meta.

The same **Webhook URL** field on the main form group is visible only
in the developer mode. Use the tab; that copy is for operators.

## Meta webhook

1. In the Meta app, open the Instagram Login product's webhook /
   callback settings.
2. Callback URL: paste the **Webhook URL** copied from Odoo.
3. Verify token: paste the same string as **Instagram Security Key**.
4. Subscribe the **`messages`** field only.
5. Meta sends a GET to Odoo. On success the gateway state becomes
   `integrated`.

The webhook endpoint must be publicly reachable over HTTPS. Self-signed
certificates are not accepted by Meta.

## 24-hour messaging window

Instagram only allows the professional account to message a user **after**
that user has messaged it, and only for **24 hours** after the user's
last message. Replies from Discuss outside that window are rejected by
Meta. Anything that must be sent later has to go through another
channel. A human-agent tag that extends the window is listed on the
module roadmap and is not implemented here.
