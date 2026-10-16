# WhatsApp setup (untested against live Meta)

The adapter is tested against mocked Graph API calls only. Expect to debug on first real contact.

1. Create a Meta app with the WhatsApp product; note the **phone number ID** and a **permanent access token**.
2. Set `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_APP_SECRET` (App Settings → Basic) and a `WHATSAPP_VERIFY_TOKEN` of your choosing.
3. Deploy over HTTPS and set `PUBLIC_BASE_URL`.
4. In the Meta dashboard, set the callback URL to `https://YOUR-HOST/webhook/whatsapp` with your verify token, and subscribe to **messages**.
5. Message the number. The bot asks for a language, then shows the menu.

Notes: interactive buttons are limited to 3, titles up to 20 characters. Meta may require message templates for conversations you start. Check current Meta policy for your category.
