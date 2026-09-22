# Crevio Bot

Telegram bot: channel-gated menu, wallet, deposits (Razorpay/INR + TRX),
masked calling (Edesy), a paid REST API for calling, and referrals.

---

## 1. Before you deploy — accounts you need

1. **Telegram bot token** — talk to `@BotFather`, `/newbot`, copy the token.
2. **Make the bot an admin** of your channel `@CrevioUpdates` (needed for the
   auto-detect join check to work — see note below).
3. **Cloudflare D1 database**
   - Cloudflare Dashboard → Workers & Pages → D1 → Create database.
   - Open its Console tab, paste the entire contents of `schema.sql` from
     this zip, and run it. This creates all 4 tables.
   - Grab your **Account ID** (right sidebar of the dashboard), the
     **Database ID** (on the D1 database's page), and create an
     **API Token** (My Profile → API Tokens → create one with
     "D1 Edit" permission).
4. **Razorpay**
   - Get your **Key ID** and **Key Secret** from Razorpay Dashboard → API Keys.
   - After deploying (step 3 below), go to Settings → Webhooks, add
     `https://<your-render-url>/razorpay-webhook`, subscribe to the
     `payment_link.paid` event, and copy the **Webhook Secret** it gives you.
5. **TRX wallet address** — any Tron wallet address you control, to receive
   deposits into.
6. **Edesy account** — sign up at their self-serve portal, fund the prepaid
   wallet, grab the API key.

---

## 2. Deploy to Render (free tier)

1. Push this folder to a GitHub repo.
2. Render Dashboard → New → Web Service → connect the repo.
3. Runtime: Python 3. Build command: `pip install -r requirements.txt`.
   Start command is already set via the included `Procfile`
   (`gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT bot:flask_app`).
   **Keep it at 1 worker** — the bot's Telegram webhook registration and
   background schedulers run once per process at startup; more than one
   worker would register the webhook repeatedly and run duplicate
   billing/TRX-checking loops.
4. Add every variable from `.env.example` in Render's **Environment** tab
   (fill in your real values — `WEBHOOK_BASE_URL` is the `https://...onrender.com`
   URL Render gives this service).
5. Deploy. On startup the bot automatically calls Telegram's `setWebhook`
   for you — no manual step needed there.

### Render free tier sleeps — keep it awake
Render's free web services go to sleep after 15 minutes with no incoming
requests. While asleep, the live call-billing and TRX-checking loops don't
run either. Use a free service like **UptimeRobot** or **cron-job.org** to
ping `https://<your-render-url>/` every 5–10 minutes, 24/7. This is not
optional if you want deposits/calls to work reliably.

---

## 3. Things you should double check / decide

I've built everything according to what we discussed, but a few pieces
were either assumptions on my part or depend on details only you can
confirm once you have real access:

- **Edesy's exact API.** I couldn't get their full API reference during
  planning — only the pricing (₹1.50/min combined) was confirmed over
  WhatsApp. `services/edesy.py` follows the standard "click-to-call
  bridge" pattern (create call with two numbers → poll status → hangup).
  Once you have their actual API docs, you may need to adjust the
  endpoint paths and the two field names marked with comments in
  `services/edesy.py` and `services/billing.py` (`status`,
  `duration_seconds`). Nothing else in the bot needs to change.
- **Calling requires the user's own phone number.** This came up as a
  technical necessity that wasn't discussed explicitly: to ring a masked
  bridge call, Edesy needs to ring *your* user first — which means the
  bot needs their real number on file. I added a one-time "📱 Share My
  Number" step (Telegram's native contact-share button) before a user's
  first call. It's stored privately and never shown to the person they
  call.
- **Referral bonus timing.** I credited the 0.3-currency referral bonus
  the moment the *referred* person verifies channel membership (not just
  `/start`, and not tied to their first deposit/call). If you'd rather
  tie it to their first deposit or first call, that's a small change in
  `handlers/general.py` (`_credit_referral_if_needed`).
- **TRX confirmations.** The Tron check currently treats any transaction
  TronGrid returns as "confirmed" (`only_confirmed=true`). Tron transactions
  confirm quickly, but if you ever see a mismatch, this is the first place
  to look (`services/tron.py`).
- **Ringing timeout.** If a call never connects, it auto-fails after 60
  seconds (`RINGING_TIMEOUT_SEC` in `services/billing.py`) so a user's
  "1 active call" slot doesn't get stuck forever.

---

## 4. What I tested (and what I couldn't, in this sandbox)

I don't have network access to `api.telegram.org`, Cloudflare, Razorpay,
Edesy, or TronGrid from where I built this, so I could not run a real
end-to-end call/payment. What I *did* verify:

- Every file compiles with no syntax errors.
- Every module imports cleanly with no missing dependencies.
- Pure logic — India number validation, TRX unique-amount collision
  avoidance, Razorpay webhook signature verification, keyboard layouts,
  message template formatting — all pass direct tests.
- `bot.py`'s Telegram initialization correctly reaches the point of
  calling Telegram's API (confirmed by the specific network error it hit
  in this sandbox, which is expected here and will not happen on Render
  with real network access).

**What this means for you:** the code is free of the errors I can catch
without live credentials (syntax, imports, logic bugs). The first real
test — with your actual Telegram token, D1, Razorpay, and Edesy keys, on
Render — may still surface small issues, mostly likely in the exact field
names Edesy's API returns (see point above). Tell me what you see and
I'll fix it.

---

## 5. File map

```
bot.py                  - entrypoint: Flask server + Telegram webhook + schedulers
config.py               - all environment variables, one place
db.py                   - Cloudflare D1 HTTP wrapper + every query
texts.py                - every message template
keyboards.py            - every inline keyboard
utils.py                - small formatting/validation helpers
schema.sql              - run once in D1's console to create tables
handlers/general.py     - /start, channel-join check, main menu, profile,
                           invite, support, info, history
handlers/rate.py        - Rate Us feature
handlers/deposit.py     - INR + TRX deposit flow
handlers/apikey.py      - API Key screen
handlers/call.py        - Make A Call flow (in-bot)
handlers/text_router.py - routes free-text replies to the right flow
services/edesy.py       - masked call provider
services/tron.py        - TronGrid incoming-payment checker
services/razorpay_service.py - payment links + webhook signature check
services/billing.py     - shared live 5-second call billing loop
services/public_api.py  - the paid REST API (for API Key holders)
```
