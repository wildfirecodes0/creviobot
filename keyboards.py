from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config


def join_channel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Crevio Updates", url=f"https://t.me/{config.CHANNEL_USERNAME.lstrip('@')}")]
    ])


def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Profile", callback_data="menu:profile"),
         InlineKeyboardButton("💎 Deposit", callback_data="menu:deposit")],
        [InlineKeyboardButton("📞 Make A Call", callback_data="menu:call")],
        [InlineKeyboardButton("🔑 API Key", callback_data="menu:apikey"),
         InlineKeyboardButton("🌐 History", callback_data="menu:history:1")],
        [InlineKeyboardButton("☎️ Take Support", callback_data="menu:support")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="menu:info"),
         InlineKeyboardButton("🫂 Invite", callback_data="menu:invite")],
    ])


def back_to_menu_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")]])


def profile_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ Rate Us", callback_data="rate:open"),
         InlineKeyboardButton("➕ Deposit", callback_data="menu:deposit")],
        [InlineKeyboardButton("🫂 Invite Your Friends", callback_data="menu:invite")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")],
    ])


def rate_us_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️❤️❤️❤️❤️", callback_data="rate:5")],
        [InlineKeyboardButton("🤎🤎🤎🤎", callback_data="rate:4")],
        [InlineKeyboardButton("💜💜💜", callback_data="rate:3")],
        [InlineKeyboardButton("💙💙", callback_data="rate:2")],
        [InlineKeyboardButton("🖤", callback_data="rate:1")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")],
    ])


def invite_kb(ref_link: str):
    share_url = f"https://t.me/share/url?url={ref_link}&text=Join%20Crevio%20Bot!"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Share Invitation Link", url=share_url)],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")],
    ])


def support_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat With Support", url=f"https://t.me/{config.SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")],
    ])


def info_kb():
    return back_to_menu_kb()


def history_list_kb(refs_with_page: list, page: int, total_pages: int):
    rows = []
    for ref in refs_with_page:
        rows.append([InlineKeyboardButton(ref, callback_data=f"hist:view:{ref}:{page}")])

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("«", callback_data=f"menu:history:{page - 1}"))
    for p in range(max(1, page - 1), min(total_pages, page + 1) + 1):
        label = f"[{p}]" if p == page else str(p)
        nav.append(InlineKeyboardButton(label, callback_data=f"menu:history:{p}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("»", callback_data=f"menu:history:{page + 1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def history_detail_kb(page: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to History", callback_data=f"menu:history:{page}")]
    ])


def deposit_method_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("INR", callback_data="dep:method:INR"),
         InlineKeyboardButton("TRX", callback_data="dep:method:TRX")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")],
    ])


def deposit_amount_kb(method: str):
    if method == "INR":
        presets = [10, 20, 50, 100, 200, 500]
        prefix = "₹"
    else:
        presets = [1, 5, 10, 30, 50, 100]
        prefix = ""
    rows = []
    rows.append([InlineKeyboardButton(f"{prefix}{presets[0]}", callback_data=f"dep:amt:{method}:{presets[0]}"),
                 InlineKeyboardButton(f"{prefix}{presets[1]}", callback_data=f"dep:amt:{method}:{presets[1]}"),
                 InlineKeyboardButton(f"{prefix}{presets[2]}", callback_data=f"dep:amt:{method}:{presets[2]}")])
    rows.append([InlineKeyboardButton(f"{prefix}{presets[3]}", callback_data=f"dep:amt:{method}:{presets[3]}"),
                 InlineKeyboardButton(f"{prefix}{presets[4]}", callback_data=f"dep:amt:{method}:{presets[4]}"),
                 InlineKeyboardButton(f"{prefix}{presets[5]}", callback_data=f"dep:amt:{method}:{presets[5]}")])
    rows.append([InlineKeyboardButton("✏️ Enter Custom Amount", callback_data=f"dep:custom:{method}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="menu:deposit")])
    return InlineKeyboardMarkup(rows)


def pay_now_kb(pay_url: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("💳 Pay Now", url=pay_url)]])


def call_confirm_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Start Call", callback_data="call:start"),
         InlineKeyboardButton("❌ Cancel", callback_data="menu:main")],
    ])


def apikey_locked_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Deposit Now", callback_data="menu:deposit")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="menu:main")],
    ])
