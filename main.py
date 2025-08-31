import os
from telegram.ext import Updater, MessageHandler, Filters

# گرفتن توکن از Environment Variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
# جایی که میخوای پیام‌ها بره (مثلا آیدی خودت یا گروه)
FORWARD_CHAT_ID = os.getenv("FORWARD_CHAT_ID")

def forward_message(update, context):
    context.bot.forward_message(
        chat_id=FORWARD_CHAT_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )

if __name__ == "__main__":
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.all, forward_message))

    updater.start_polling()
    updater.idle()
