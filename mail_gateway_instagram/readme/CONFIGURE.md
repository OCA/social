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
   - **Show Own Messages**: when enabled, messages the professional
     account sends from the Instagram app are posted in the Discuss
     gateway channel. Default is off, so existing databases keep
     ignoring those echoes until an operator turns it on. Echoed
     messages are authored as **Webhook User**, which defaults to
     OdooBot (`base.user_root`).
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

## Outbound media

Sending an image, audio, video or PDF from Discuss needs a **public**
`web.base.url` that Meta's media fetcher can download **while the send
is still running**. Instagram Login only accepts `payload.url` (Meta
GETs the file); there is no multipart upload on that API. A localhost
URL will fail. Graph error 2018007 (`Upload failed` /
`Upload fehlgeschlagen` / `Caricamento non riuscito`) means that fetch
did not return the file.

Outbound media uses
`/mail_gateway_instagram/content/<id>/<token>/<filename>` (token in the
path, no query string). Core Odoo `robots.txt` is `Disallow: /`; this
module lists `Allow: /mail_gateway_instagram/content` first (including
for `facebookexternalhit`) so Meta's crawler is not blocked. If the
**Website** app is installed and its robots.txt still disallows the
path, add the same Allow line there. Graph's error body is stored on
the Discuss notification.

### Host reachability (2018007 with a working URL)

A browser (or your own curl) returning HTTP 200 for the media URL is
**not** enough. Meta's media fetcher is a separate service from the
webhook client:

- Webhooks can POST successfully to the same host while media GETs
  still fail with 2018007.
- When the hostname resolves to a bare datacenter IP (for example a
  Hetzner VPS with Cloudflare DNS-only / grey cloud), Meta often
  **never opens a TCP connection** to that host. Access logs show no
  GET from Meta, and Graph fails in under a second. Cloudflare "AI bot
  access" / robots settings do not apply on grey-cloud traffic.
- The same Graph token and recipient can send images whose
  `payload.url` points at a public CDN (Cloudflare, GitHub raw,
  httpbin, and similar) while URLs on the Odoo host keep failing.

Mitigations: put the media hostname behind a CDN or Cloudflare
**proxied** (orange cloud) record, or serve outbound files from object
storage / a CDN base URL that Meta will fetch. Changing only the Odoo
path shape will not fix a host Meta refuses to contact.

Each send publishes a **permanent unauthenticated** tokenized media
URL (`access_token` on `ir.attachment`) until an operator clears that
token. Do not treat those URLs as private.

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
