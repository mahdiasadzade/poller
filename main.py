import os
from zoneinfo import ZoneInfo
from datetime import datetime, time, timedelta
import jdatetime  # تاریخ شمسی
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHAT_IDS = [int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",") if x.strip()]
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

# مسیر ذخیره لاگ‌ها
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# کلمات حساس برای هشدار 🚨
ALERT_WORDS = ["پسورد", "رمز", "password", "پول", "ویزا"]
ALERT_CHAT_ID = int(os.getenv("ALERT_CHAT_ID", "0"))  # میتونه همون مقصد باشه


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg:
        return

    from_chat = update.effective_chat
    from_user = update.effective_user
    from_id = from_chat.id

    # بررسی مبدأ
    if SOURCE_CHAT_IDS != ["*"] and str(from_id) not in SOURCE_CHAT_IDS:
        return

    # زمان پیام
    try:
        dt_utc = msg.date.replace(tzinfo=ZoneInfo("UTC"))
    except Exception:
        dt_utc = datetime.now(tz=ZoneInfo("UTC"))

    dt_iran = dt_utc.astimezone(ZoneInfo("Asia/Tehran"))

    # تاریخ شمسی
    dt_jalali = jdatetime.datetime.fromgregorian(datetime=dt_iran)
    date_str = dt_jalali.strftime("%Y/%m/%d")
    time_str = dt_iran.strftime("%H:%M:%S")

    # متن اصلی
    sender_info = (
        f"📩 پیام جدید\n"
        f"👤 {from_user.full_name} | 🆔 {from_user.id}\n"
        f"👥 {from_chat.title or from_chat.full_name or from_chat.id}\n"
        f"🕒 {date_str} - {time_str} (ایران)"
    )

    # ارسال به مقصدها
    for chat_id in DEST_CHAT_IDS:
        await context.bot.send_message(chat_id=chat_id, text=sender_info)
        await context.bot.copy_message(chat_id=chat_id, from_chat_id=from_id, message_id=msg.message_id)

    # نوشتن لاگ (utf-8)
    safe_chatname = (from_chat.title or from_chat.full_name or str(from_id)).replace(" ", "_")
    log_filename = os.path.join(LOG_DIR, f"chat_{safe_chatname}_{date_str}.txt")

    log_line = f"[{date_str} {time_str}] {from_user.full_name} ({from_user.id}): {msg.text or '<non-text>'}\n"
    try:
        with open(log_filename, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print("Log write error:", e)

    # سیستم هشدار زنده
    text_lower = (msg.text or "").lower()
    if any(word in text_lower for word in ALERT_WORDS):
        if ALERT_CHAT_ID:
            await context.bot.send_message(
                chat_id=ALERT_CHAT_ID,
                text=f"🚨 هشدار! پیام مشکوک از {from_user.full_name}:\n{msg.text}"
            )


async def send_daily_logs(context: ContextTypes.DEFAULT_TYPE):
    """هر شب بعد از نیمه‌شب گزارش روز قبل رو میفرسته"""
    dt_iran = datetime.now(ZoneInfo("Asia/Tehran")) - timedelta(days=1)
    dt_jalali = jdatetime.datetime.fromgregorian(datetime=dt_iran)
    date_str = dt_jalali.strftime("%Y/%m/%d")
    date_filename = dt_jalali.strftime("%Y-%m-%d")

    for file in os.listdir(LOG_DIR):
        if file.endswith(f"{date_filename}.txt"):
            filepath = os.path.join(LOG_DIR, file)
            for chat_id in DEST_CHAT_IDS:
                try:
                    with open(filepath, "rb") as doc:
                        await context.bot.send_document(chat_id=chat_id, document=doc, caption=f"📑 گزارش روز {date_str}")
                except Exception as e:
                    print("Send daily log error:", e)


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    # تنظیم ارسال گزارش هر روز ساعت 00:05 به وقت ایران
    iran_now = datetime.now(ZoneInfo("Asia/Tehran"))
    first_time = datetime.combine(iran_now.date(), time(0, 5, tzinfo=ZoneInfo("Asia/Tehran")))
    if iran_now > first_time:
        first_time += timedelta(days=1)

    app.job_queue.run_repeating(
        send_daily_logs,
        interval=timedelta(days=1),
        first=first_time
    )

    print("Bot started ✅")
    app.run_polling()
