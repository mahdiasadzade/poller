import os
from zoneinfo import ZoneInfo
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHAT_IDS = [int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",") if x.strip()]
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

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

    timestamp_utc = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    dt_iran = dt_utc.astimezone(ZoneInfo("Asia/Tehran"))
    timestamp_iran = dt_iran.strftime("%Y-%m-%d %H:%M:%S IRST")

    # نوع پیام + حجم/مدت
    msg_type = "متن"
    extra_info = ""
    if msg.voice:
        msg_type = "وویس"
        extra_info = f"⏱ {msg.voice.duration} ثانیه"
    elif msg.video:
        msg_type = "ویدیو"
        dur = getattr(msg.video, "duration", None)
        size = getattr(msg.video, "file_size", None)
        extra_info = (f"⏱ {dur} ثانیه | 📦 {size/1024:.1f} KB") if dur or size else ""
    elif msg.document:
        msg_type = "فایل"
        size = getattr(msg.document, "file_size", None)
        extra_info = f"📦 {size/1024:.1f} KB" if size else ""
    elif msg.photo:
        msg_type = "عکس"
    elif msg.sticker:
        msg_type = f"استیکر {msg.sticker.emoji or ''}"

    # کلاینت/بات مبدا
    if msg.via_bot:
        client_info = f"📱 ارسال از طریق: @{msg.via_bot.username}"
    else:
        client_info = "📱 کلاینت: نامشخص"

    # لینک پیام
    if from_chat.username:
        msg_link = f"https://t.me/{from_chat.username}/{msg.message_id}"
    elif from_chat.type in ["supergroup", "channel"]:
        internal = str(from_chat.id)
        if internal.startswith("-100"):
            internal_id = internal[4:]
        else:
            internal_id = internal.lstrip("-")
        msg_link = f"https://t.me/c/{internal_id}/{msg.message_id}"
    else:
        msg_link = "لینک: (پرایوت)"

    # ریپلای
    if msg.reply_to_message:
        reply_msg = msg.reply_to_message
        reply_user = reply_msg.from_user.full_name if reply_msg.from_user else "نامشخص"
        reply_preview = (reply_msg.text[:80] + "...") if (reply_msg.text and len(reply_msg.text) > 80) else (reply_msg.text or "📎 غیرمتنی")
        reply_info = f"↩️ ریپلای به: {reply_user} | «{reply_preview}»"
    else:
        reply_info = "↩️ بدون ریپلای"

    # متن اطلاعاتی
    sender_info = (
        f"📩 پیام جدید\n"
        f"🕒 زمان (UTC): {timestamp_utc}\n"
        f"🕒 زمان (ایران): {timestamp_iran}\n"
        f"👤 نام: {from_user.full_name}\n"
        f"🆔 آیدی: {from_user.id}\n"
        f"🔗 یوزرنیم: @{from_user.username if from_user.username else 'ندارد'}\n"
        f"👥 چت/گروه: {from_chat.title or from_chat.full_name or from_chat.id}\n"
        f"📌 نوع پیام: {msg_type} {extra_info}\n"
        f"{client_info}\n"
        f"{reply_info}\n"
        f"🔗 لینک پیام: {msg_link}"
    )

    # اسم فایل لاگ (بر اساس نام گپ و تاریخ)
    safe_chatname = (from_chat.title or from_chat.full_name or str(from_id)).replace(" ", "_")
    date_str = dt_iran.strftime("%Y-%m-%d")
    log_filename = f"chat_{safe_chatname}_{date_str}.txt"

    log_line = f"[{timestamp_iran}] {from_user.full_name} ({from_user.id}): {msg.text or '<non-text>'}\n"

    # ارسال به مقصدها
    for chat_id in DEST_CHAT_IDS:
        # ارسال info
        await context.bot.send_message(chat_id=chat_id, text=sender_info)
        # کپی پیام اصلی
        await context.bot.copy_message(chat_id=chat_id, from_chat_id=from_id, message_id=msg.message_id)

        # نوشتن لاگ
        try:
            with open(log_filename, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            print("Log write error:", e)

        # ارسال فایل لاگ
        try:
            with open(log_filename, "rb") as doc:
                await context.bot.send_document(chat_id=chat_id, document=doc)
        except Exception as e:
            print("Send log file error:", e)

    # سیستم هشدار
    text_lower = (msg.text or "").lower()
    if any(word in text_lower for word in ALERT_WORDS):
        if ALERT_CHAT_ID:
            await context.bot.send_message(
                chat_id=ALERT_CHAT_ID,
                text=f"🚨 هشدار! پیام مشکوک از {from_user.full_name}:\n{msg.text}"
            )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot started ✅")
    app.run_polling()
