import os
from telegram.ext import Updater, MessageHandler, Filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

# لیست مبداها (source) با کاما جدا می‌کنیم
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

# لیست مقصدها
DEST_CHAT_IDS = os.getenv("DEST_CHAT_IDS", "").split(",")

def forward_message(update, context):
    from_id = update.message.chat_id
    # اگر * بود، همه رو قبول کن
    if SOURCE_CHAT_IDS != ["*"] and str(from_id) not in SOURCE_CHAT_IDS:
        return

    for chat_id in DEST_CHAT_IDS:
        chat_id = int(chat_id.strip())
        context.bot.forward_message(
            chat_id=chat_id,
            from_chat_id=from_id,
            message_id=update.message.message_id
        )

if __name__ == "__main__":
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.all, forward_message))

    updater.start_polling()
    updater.idle()
