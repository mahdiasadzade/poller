import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHAT_IDS = [int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",")]
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_chat = update.effective_chat
    from_user = update.effective_user
    from_id = from_chat.id

    if SOURCE_CHAT_IDS != ["*"] and str(from_id) not in SOURCE_CHAT_IDS:
        return

    sender_info = (
        f"📩 پیام از:\n"
        f"نام: {from_user.full_name}\n"
        f"آیدی: {from_user.id}\n"
        f"یوزرنیم: @{from_user.username if from_user.username else 'ندارد'}\n"
        f"گروه/چت: {from_chat.title or from_chat.full_name or from_chat.id}"
    )

    for chat_id in DEST_CHAT_IDS:
        # اول info فرستنده
        await context.bot.send_message(chat_id=chat_id, text=sender_info)
        # بعد پیام اصلی رو کپی کن
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_id,
            message_id=update.effective_message.message_id
        )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot started (async, Python 3.13 compatible)")
    app.run_polling()
