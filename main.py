import os
import asyncio
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHAT_IDS = [int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",")]
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_id = update.effective_chat.id
    if SOURCE_CHAT_IDS != ["*"] and str(from_id) not in SOURCE_CHAT_IDS:
        return

    for chat_id in DEST_CHAT_IDS:
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_id,
            message_id=update.effective_message.message_id
        )

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot started (async, Python 3.13 compatible)")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
