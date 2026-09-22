"""
Every user-facing message lives here so wording can be tweaked without
touching handler logic. All placeholders are filled with .format(**kwargs).
"""
import config

WELCOME_LOCKED = """👋 <b>Welcome, {first_name}!</b>

✨ Welcome to <b>Crevio Bot</b> — your access to exclusive premium channels.

<b>🔐 Join our official channel to continue. 👇</b>"""

WELCOME_MENU = "✨ <b>Welcome To CrevioBot.</b>"

PROFILE = """👤 <b>Name:</b> <a href="tg://user?id={telegram_id}">{first_name}</a>
🆔 <b>Telegram ID:</b> <code>{telegram_id}</code>

💰 <b>Balance:</b> <code>{balance}</code> <b>{currency}</b>

💴 <b>Total Spent:</b> <code>{total_spent}</code> <b>{currency}</b>
🏖 <b>Total Purchased:</b> {total_minutes} min

💕 <b>Joining Date:</b> {joining_date}"""

RATE_US_PROMPT = "<b>💛 Please Rate Us :</b>"

RATE_US_ALREADY = "You Have Already Rated."
RATE_US_THANKS = "Thanks For Rating Us"

RATING_BROADCAST = """<b>❤ New Rating Received ❤</b>

👷 {first_name} <b>have Rated us:~</b> {stars} <i>({num_stars} Star 🌟)</i>

📞 <i>Call Your Favourites From Here➡️  {channel}</i>"""

INVITE_DASHBOARD = """🎯 <b>Your Referral Dashboard</b>

Invite your friends and earn together.

🔗 <b>Your Referral Link:</b>
<code>{ref_link}</code>

👥 <b>Total Referrals:</b> {ref_count}
🪙 <b>Total Earning:</b> {ref_earning} {currency}

💡 <i>You'll earn</i> <b>{bonus} {currency}</b> <i>straight to your wallet for every successful referral.</i>"""

SUPPORT_TEXT = """☎️ <b>Support Center</b>

Stuck somewhere? Got a question? We're just one tap away.

🕐 <b>Response Time:</b> Usually within a few minutes
🙌 <b>Available:</b> 24/7

Tap below to chat with our team directly 👇"""

INFO_TEXT = """📞 <b>CREVIO BOT</b>
<i>One number. One call. One conversation.</i>

<b>Want to talk to someone without dialing them yourself?</b> 👀

With <b>Crevio Bot</b>, just share the number — we'll handle the rest. No app-switching, no hassle.

📱 <b>Enter</b> the number
🔗 Get <b>connected</b>
🎙️ Start <b>talking</b>

<b>Crevio Bot</b> — Connect. Call. Talk.

⚠️ <b><i>Use Crevio Bot responsibly.</i></b> <i>Only connect with numbers that have given consent. Spam, harassment, or misuse will not be tolerated.</i>"""

HISTORY_HEADER = "🌐 <b>Your History</b>\n\n"
HISTORY_EMPTY = "🌐 <b>Your History</b>\n\n<i>No transactions yet.</i>"
HISTORY_TAP_LINE = "\n👇<i>Tap any reference ID to view full details.</i>"

HISTORY_DETAIL_CALL = """📄 <b>Transaction Details</b>

🆔 <b>Reference ID:</b> <code>{ref_id}</code>
📌 <b>Type:</b> 📞 Call

📱 <b>Number:</b> {number}
⏱️ <b>Duration:</b> {duration} min
💸 <b>Amount Deducted:</b> {amount} {currency}

📅 <b>Date:</b> {date}
✅ <b>Status:</b> {status}"""

HISTORY_DETAIL_DEPOSIT = """📄 <b>Transaction Details</b>

🆔 <b>Reference ID:</b> <code>{ref_id}</code>
📌 <b>Type:</b> 💎 Deposit

💰 <b>Amount:</b> {amount} {currency}
💳 <b>Method:</b> {method}

📅 <b>Date:</b> {date}
✅ <b>Status:</b> {status}"""

DEPOSIT_INTRO = """<b>👋 Welcome!</b>
Here You Can Add Funds To Your Balance!

<b>➕ Select Deposit Method,</b> All deposits will be converted to <b>{currency}</b>

<i>⚡Minimum Deposit is 10 rs or 1 trx.</i>

📍 1 INR = 1 {currency} <b>(0% TAX)</b>
📍 1 TRX = 30 {currency} <b>(0% TAX)</b>

<b>⚠️ NOTE:</b> If You Once Deposited Successfully Then Your Fund Can't Be Able To Withdraw."""

DEPOSIT_PICK_AMOUNT = "Select an amount, or enter your own 👇"

DEPOSIT_CUSTOM_ASK_INR = "✏️ Enter the amount (in INR) you want to deposit:"
DEPOSIT_CUSTOM_ASK_TRX = "✏️ Enter the amount (in TRX) you want to deposit:"

DEPOSIT_DETAILS_INR = """💎 <b>Deposit Details</b>

💰 <b>Amount:</b> ₹{amount}

⏰ <b>Time Left:</b> {minutes}:00 minutes

⚠️ <b>Important:</b>
• Complete payment <b>within {minutes} minutes</b>
• After {minutes} minutes this link will expire

👇 Tap below to pay"""

DEPOSIT_DETAILS_TRX = """💎 <b>Deposit Details</b>

📍 <b>Send exactly:</b> <code>{amount} TRX</code>
📥 <b>To Address:</b>
<code>{wallet}</code>

⏰ <b>Time Left:</b> {minutes}:00 minutes

<b>📌 Please Note:</b>
• Send the <b>exact amount</b> shown above
• Complete the payment within the given time
• Deposits with a different amount or done after time runs out won't be credited"""

DEPOSIT_MIN_ERROR_INR = "⚠️ Minimum deposit is ₹10. Please enter a higher amount."
DEPOSIT_MIN_ERROR_TRX = "⚠️ Minimum deposit is 1 TRX. Please enter a higher amount."
DEPOSIT_INVALID_NUMBER = "⚠️ Please enter a valid number."

API_LOCKED = """🔑 <b>API Access Locked</b>

⚠️ <i>You need a minimum balance of</i> <b>{min_balance} {currency}</b> <i>to unlock API access.</i>

💰 <b>Current Balance:</b> <code>{balance} {currency}</code>

📥 <i>Deposit more funds to get instant access to your personal calling API.</i>"""

API_UNLOCKED = """🔑 <b>Your API Access</b>

✅ <i>You're eligible! Your balance meets the minimum requirement.</i>

🌐 <b>API Endpoint:</b>
<code>{endpoint}</code>

🔐 <b>Your API Key:</b>
<code>{api_key}</code>

💸 <i>Every call made through this API will deduct directly from your bot balance.</i>

📄 <i>Use this key in your Authorization header to make requests:</i>
<code>Authorization: Bearer {api_key}</code>"""

CALL_ASK_NUMBER = """📞 <b>Make A Call</b>

Enter the phone number you want to call.
(with country code, e.g. +91XXXXXXXXXX)

⚠️ <i>Only use numbers with the person's consent. Misuse is not allowed.</i>"""

CALL_INVALID_NUMBER = "⚠️ Only Indian numbers (+91XXXXXXXXXX) are supported. Please try again."

CALL_ALREADY_ACTIVE = "⚠️ You already have an active call. Please finish it before starting a new one."

CALL_INSUFFICIENT_BALANCE = """⚠️ <b>Insufficient Balance</b>

You need at least {min_minutes} minute(s) worth of balance to start a call.

💰 <b>Current Balance:</b> {balance} {currency}
💵 <b>Rate:</b> {rate} {currency}/min"""

CALL_CONFIRM = """📞 <b>Confirm Your Call</b>

📱 <b>Number:</b> {number}
💰 <b>Rate:</b> {rate} {currency}/min
💳 <b>Your Balance:</b> {balance} {currency}
⏱️ <b>Max Talk Time (at current balance):</b> {max_minutes} min

Proceed with the call?"""

CALL_STARTING = "📞 Connecting your call... you'll be rung first, then connected to the number."

CALL_ENDED = """📞 <b>Call Ended</b>

⏱️ <b>Duration:</b> {duration} min
💸 <b>Charged:</b> {amount} {currency}
💰 <b>Remaining Balance:</b> {balance} {currency}"""

CALL_FAILED = "⚠️ The call could not be connected. No amount has been charged."

GENERIC_ERROR = "⚠️ Something went wrong. Please try again in a moment."
