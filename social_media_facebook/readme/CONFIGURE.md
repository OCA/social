## Odoo Configuration

1. Go to **Settings** > **Social Media**
2. In the **Facebook App Credentials** section:
   - Enter your **App ID**
   - Enter your **App Secret**
   - Copy the **Redirect URI** (you'll need this for Facebook)

## Facebook App Setup

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new App or use an existing one
3. Add the following products to your app:
   - **Facebook Login** (required for authentication)
   - **Pages API** (required for posting)
   - **Webhooks** (optional, for real-time lead sync)
4. In Facebook Login Settings:
   - Add the **Redirect URI** from Odoo to **Valid OAuth Redirect URIs**
5. In Settings > Basic:
   - Copy your **App ID** and **App Secret** to Odoo

## Connect Facebook Account

1. Go to **Social Media** > **Media**
2. Select **Facebook** media type
3. Click **Add Account** button
4. Follow the OAuth flow to authorize the app
5. Select which Facebook Pages you want to connect
6. Save the configuration

## Lead Ads Webhook Setup (Optional)

For real-time lead synchronization:

1. In Odoo, go to **Settings** > **Social Media**
2. In the **Lead Ads Webhook** section:
   - Set a secure **Verify Token** (use a random string)
   - Copy the **Webhook URL**
3. In Facebook Developers:
   - Go to your App > **Webhooks**
   - Click **Add Subscription** for **Page**
   - Paste the **Webhook URL** as Callback URL
   - Paste the **Verify Token** (must match Odoo)
   - Click **Verify and Save**
   - Subscribe to the **leadgen** field

**Note:** Your Odoo instance must be accessible via HTTPS for webhooks to work.
