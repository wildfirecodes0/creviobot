from telegram import Update
from telegram.ext import ContextTypes

from handlers import deposit as deposit_handlers
from handlers import call as call_handlers


async def route_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return  # not part of any flow — ignore silently

    kind = awaiting[0]
    if kind == "deposit_custom":
        method = awaiting[1]
        await deposit_handlers.handle_custom_amount_text(update, context, method)
    elif kind == "call_number":
        await call_handlers.handle_call_number_text(update, context)
