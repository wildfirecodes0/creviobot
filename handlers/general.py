import json
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

import config
import db
import texts
import keyboards
from utils import fmt, ref_link

log = logging.getLogger("crevio.general")


async def is_channel_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=config.CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.warning("get_chat_member failed for %s: %s", user_id, e)
        return False


async def send_main_menu(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    await context.bot.send_message(
        chat_id=chat_id,
        text=texts.WELCOME_MENU,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboards.main_menu_kb(),
    )


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_by = None
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            try:
                candidate = int(arg.replace("ref_", ""))
                if candidate != user.id:
                    ref_by = candidate
            except ValueError:
                pass

    row = db.create_user_if_missing(user.id, user.first_name or "Friend", user.username, ref_by)
    db.update_first_name_username(user.id, user.first_name or "Friend", user.username)

    joined = await is_channel_member(context, user.id)
    if joined and not row.get("joined_channel"):
        db.set_joined_channel(user.id, True)
        await _credit_referral_if_needed(context, row)

    if joined:
        await send_main_menu(context, update.effective_chat.id)
    else:
        await update.message.reply_text(
            texts.WELCOME_LOCKED.format(first_name=user.first_name or "Friend"),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.join_channel_kb(),
        )


async def _credit_referral_if_needed(context, row):
    """Referral bonus is credited the first time the referred user verifies channel membership."""
    ref_by = row.get("ref_by")
    if ref_by:
        db.increment_referral(ref_by, config.REFERRAL_BONUS)
        try:
            await context.bot.send_message(
                chat_id=ref_by,
                text=f"🎉 Your referral joined and verified! You've earned <b>{config.REFERRAL_BONUS} {config.BOT_CURRENCY}</b>.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when someone's membership status changes in the channel (bot must be admin there)."""
    cmu = update.chat_member
    chat_username = f"@{cmu.chat.username}" if cmu.chat.username else None
    if chat_username != config.CHANNEL_USERNAME:
        return

    new_status = cmu.new_chat_member.status
    user = cmu.new_chat_member.user
    if new_status in ("member", "administrator", "creator"):
        existing = db.get_user(user.id)
        if existing is None:
            return  # user never pressed /start, nothing we can message
        if not existing.get("joined_channel"):
            db.set_joined_channel(user.id, True)
            await _credit_referral_if_needed(context, existing)
        try:
            await send_main_menu(context, user.id)
        except Exception as e:
            log.warning("Could not DM user %s after join: %s", user.id, e)


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles every callback_data starting with 'menu:'."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    row = db.get_user(user_id)
    if row is None:
        row = db.create_user_if_missing(user_id, query.from_user.first_name or "Friend", query.from_user.username)

    await query.answer()

    if data == "menu:main":
        await query.edit_message_text(texts.WELCOME_MENU, parse_mode=ParseMode.HTML,
                                       reply_markup=keyboards.main_menu_kb())

    elif data == "menu:profile":
        text = texts.PROFILE.format(
            telegram_id=row["telegram_id"],
            first_name=row["first_name"],
            balance=fmt(row["balance"]),
            total_spent=fmt(row["total_spent"]),
            total_minutes=f"{row['total_minutes']:.0f} min" if row['total_minutes'] else "0 min",
            joining_date=row["joining_date"][:10],
            currency=config.BOT_CURRENCY,
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.profile_kb())

    elif data == "menu:invite":
        me = await context.bot.get_me()
        link = ref_link(me.username, user_id)
        text = texts.INVITE_DASHBOARD.format(
            ref_link=link,
            ref_count=row["ref_count"],
            ref_earning=fmt(row["ref_earning"]),
            currency=config.BOT_CURRENCY,
            bonus=config.REFERRAL_BONUS,
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.invite_kb(link))

    elif data == "menu:support":
        await query.edit_message_text(texts.SUPPORT_TEXT, parse_mode=ParseMode.HTML,
                                       reply_markup=keyboards.support_kb())

    elif data == "menu:info":
        await query.edit_message_text(texts.INFO_TEXT, parse_mode=ParseMode.HTML,
                                       reply_markup=keyboards.info_kb())

    elif data.startswith("menu:history:"):
        page = int(data.split(":")[2])
        await render_history(query, user_id, page)

    elif data == "menu:deposit":
        text = texts.DEPOSIT_INTRO.format(currency=config.BOT_CURRENCY)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.deposit_method_kb())

    elif data == "menu:apikey":
        from handlers.apikey import render_apikey
        await render_apikey(query, row)

    elif data == "menu:call":
        from handlers.call import start_call_flow
        await start_call_flow(update, context, row)


async def render_history(query, user_id: int, page: int):
    rows, total = db.get_transactions_page(user_id, page, config.HISTORY_PAGE_SIZE)
    if total == 0:
        await query.edit_message_text(texts.HISTORY_EMPTY, parse_mode=ParseMode.HTML,
                                       reply_markup=keyboards.back_to_menu_kb())
        return

    total_pages = max(1, (total + config.HISTORY_PAGE_SIZE - 1) // config.HISTORY_PAGE_SIZE)
    lines = [texts.HISTORY_HEADER]
    refs = []
    start_num = (page - 1) * config.HISTORY_PAGE_SIZE + 1
    for i, r in enumerate(rows):
        lines.append(f"<b>{start_num + i}.</b> <i>{r['ref_id']}</i>\n")
        refs.append(r["ref_id"])
    text = "".join(lines) + texts.HISTORY_TAP_LINE

    await query.edit_message_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=keyboards.history_list_kb(refs, page, total_pages),
    )


async def history_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":", 3)
    _, _, ref_id, page = parts
    page = int(page)
    tx = db.get_transaction_by_ref(ref_id)
    if not tx:
        await query.edit_message_text(texts.GENERIC_ERROR, reply_markup=keyboards.back_to_menu_kb())
        return

    detail = json.loads(tx["detail_json"] or "{}")
    date = tx["created_at"][:16].replace("T", " ")

    if tx["type"] == "call":
        text = texts.HISTORY_DETAIL_CALL.format(
            ref_id=ref_id,
            number=detail.get("number", "-"),
            duration=detail.get("duration_min", "0"),
            amount=fmt(tx["amount"]),
            currency=config.BOT_CURRENCY,
            date=date,
            status=tx["status"].capitalize(),
        )
    else:
        text = texts.HISTORY_DETAIL_DEPOSIT.format(
            ref_id=ref_id,
            amount=fmt(tx["amount"]),
            currency=config.BOT_CURRENCY,
            method=tx["method"] or "-",
            date=date,
            status=tx["status"].capitalize(),
        )

    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.history_detail_kb(page))
