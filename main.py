import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import jdatetime
from telegram import Update, Message
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHAT_IDS = [int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",")]
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def iran_now():
    return datetime.now(ZoneInfo("Asia/Tehran"))

def save_daily_log():
    """گزارش روزانه دیروز بسازه"""
    yesterday = iran_now() - timedelta(days=1)
    daily_content = ""
    for file in os.listdir(LOG_DIR):
        if file.endswith(f"{yesterday.strftime('%Y-%m-%d')}.txt"):
            with open(os.path.join(LOG_DIR, file), "r", encoding="utf-8") as f:
                daily_content += f.read() + "\n"
    if daily_content:
        daily_file = os.path.join(LOG_DIR, f"daily_log_{yesterday.strftime('%Y-%m-%d')}.txt")
        with open(daily_file, "w", encoding="utf-8") as f:
            f.write(daily_content)
        print(f"Daily log saved: {daily_file}")

def get_message_type(message: Message):
    if message.text:
        return "متن"
    elif message.photo:
        return "عکس"
    elif message.video:
        return "ویدئو"
    elif message.document:
        return "فایل"
    elif message.audio:
        return "صوت"
    elif message.voice:
        return "ویس"
    elif message.sticker:
        return "استیکر"
    elif message.video_note:
        return "وینوته"
    else:
        return "سایر"

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_chat = update.effective_chat
    from_user = update.effective_user
    from_id = from_chat.id
    message = update.effective_message

    if SOURCE_CHAT_IDS != ["*"] and str(from_id) not in SOURCE_CHAT_IDS:
        return

    iran_time = iran_now()
    date_jalali = jdatetime.datetime.fromgregorian(datetime=iran_time).strftime("%Y/%m/%d")
    time_str = iran_time.strftime("%H:%M:%S")

    msg_type = get_message_type(message)
    client_info = message.via_bot.name if message.via_bot else "نامعلوم"
    reply_to = f"{message.reply_to_message.message_id}" if message.reply_to_message else "ندارد"
    try:
        link = await context.bot.get_chat(from_id)
        message_link = message.link if hasattr(message, 'link') else "ندارد"
    except:
        message_link = "ندارد"

    log_text = (
        "📩 پیام از:\n"
        f"👤 نام: {from_user.full_name}\n"
        f"🆔 آیدی: {from_user.id}\n"
        f"🔗 یوزرنیم: @{from_user.username if from_user.username else 'ندارد'}\n"
        f"👥 چت/گروه: {from_chat.title or from_chat.full_name or from_chat.id}\n"
        f"📌 نوع پیام: {msg_type}\n"
        f"📱 کلاینت: {client_info}\n"
        f"↩️ ریپلای به: {reply_to}\n"
        f"🔗 لینک پیام: {message_link}\n"
        f"🕒 تاریخ شمسی: {date_jalali} | ساعت: {time_str}"
    )

    # فوروارد به چت مقصد
    for chat_id in DEST_CHAT_IDS:
        await context.bot.send_message(chat_id=chat_id, text=log_text)
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_id,
            message_id=message.message_id
        )

    # ذخیره لاگ روی دیسک
    log_file = os.path.join(LOG_DIR, f"{from_chat.title or from_chat.id}_{iran_time.strftime('%Y-%m-%d')}.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_text + "\n\n")

if __name__ == "__main__":
    save_daily_log()  # قبل از استارت، گزارش روز قبل بسازه
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot started (async, Python 3.13 compatible)")
    app.run_polling()
