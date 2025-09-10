import logging
from telegram import Update, MessageEntity
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import jdatetime
import pytz
import os

# فعال کردن لاگ برای دیباگ
logging.basicConfig(level=logging.INFO)

# توکن ربات
BOT_TOKEN = os.getenv("BOT_TOKEN")

# آیدی چت مقصد
DEST_CHAT_IDS = [int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",")]  # جایگزین کن

# ساختار گزارش پیام
async def build_report(message: Update.message) -> str:
    user = message.from_user
    chat = message.chat

    # تاریخ به وقت ایران و شمسی
    iran_tz = pytz.timezone("Asia/Tehran")
    now_tehran = jdatetime.datetime.now(iran_tz)
    date_str = now_tehran.strftime("%Y/%m/%d %H:%M:%S")

    # فیلدها
    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    user_id = user.id
    username = f"@{user.username}" if user.username else "ندارد"
    chat_title = chat.title if chat.title else "پی‌وی"
    msg_type = message.effective_attachment.__class__.__name__ if message.effective_attachment else "متن"
    client = message.via_bot.username if message.via_bot else "نامشخص"
    reply_to = message.reply_to_message.from_user.first_name if message.reply_to_message else "ندارد"

    # لینک پیام (فقط برای گروه/سوپرگروه با یوزرنیم عمومی)
    if chat.username:
        link = f"https://t.me/{chat.username}/{message.message_id}"
    else:
        link = "لینک ندارد"

    # متن پیام اگه متنی بود
    text_part = ""
    if message.text or message.caption:
        text_part = f"\n📩 متن:\n{message.text or message.caption}"

    report = (
        f"📩 پیام از:\n"
        f"👤 نام: {name}\n"
        f"🆔 آیدی: {user_id}\n"
        f"🔗 یوزرنیم: {username}\n"
        f"👥 چت/گروه: {chat_title}\n"
        f"📌 نوع پیام: {msg_type}"
        f"{text_part}\n\n"
        f"📱 کلاینت: {client}\n"
        f"↩️ ریپلای به: {reply_to}\n"
        f"🔗 لینک پیام: {link}\n"
        f"🕒 تاریخ شمسی: {date_str}"
    )
    return report


# هندلر پیام‌ها
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    report = await build_report(message)

    # اگر متن بود: فقط گزارش بفرسته
    if message.text:
        await context.bot.send_message(chat_id=DEST_CHAT_ID, text=report)
    else:
        # اگر غیرمتنی بود: گزارش + فوروارد پیام
        await context.bot.send_message(chat_id=DEST_CHAT_ID, text=report)
        await message.forward(chat_id=DEST_CHAT_ID)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.ALL, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()

