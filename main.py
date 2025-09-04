import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import jdatetime
from telegram import Update
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
    date_jalali = jdatetime.datetime.fromgregorian(datetime=yesterday).strftime("%Y/%m/%d")
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

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_chat = update.effective_chat
    from_user = update.effective_user
    from_id = from_chat.id

    if SOURCE_CHAT_IDS != ["*"] and str(from_id) not in SOURCE_CHAT_IDS:
        return

    iran_time = iran_now()
    date_jalali = jdatetime.datetime.fromgregorian(datetime=iran_time).strftime("%Y/%m/%d")
    time_str = iran_time.strftime("%H:%M:%S")

    sender_info = (
        f"📩 پیام از:\n"
        f"نام: {from_user.full_name}\n"
        f"آیدی: {from_user.id}\n"
        f"یوزرنیم: @{from_user.username if from_user.username else 'ندارد'}\n"
        f"گروه/چت: {from_chat.title or from_chat.full_name or from_chat.id}\n"
        f"تاریخ شمسی: {date_jalali} | ساعت: {time_str}"
    )

    for chat_id in DEST_CHAT_IDS:
        await context.bot.send_message(chat_id=chat_id, text=sender_info)
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_id,
            message_id=update.effective_message.message_id
        )

    # ذخیره لاگ روی دیسک
    log_file = os.path.join(LOG_DIR, f"{from_chat.title or from_chat.id}_{iran_time.strftime('%Y-%m-%d')}.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(sender_info + "\n" + (update.effective_message.text or "") + "\n\n")

if __name__ == "__main__":
    save_daily_log()  # قبل از استارت، گزارش روز قبل بسازه
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot started (async, Python 3.13 compatible)")
    app.run_polling()
