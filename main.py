import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import jdatetime

from telegram import Update, Message
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- Config (from environment) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHAT_IDS = [
    int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",") if x.strip()
]
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# --- Helpers ---
def iran_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Tehran"))

def safe_name(name: str) -> str:
    """Make a filesystem-safe name for chat/title."""
    if not name:
        return "unknown"
    # replace spaces and unsafe chars with underscore
    return re.sub(r"[^\w\-\.]", "_", name)

def save_daily_log():
    """
    Aggregate all per-chat files from yesterday into one daily file.
    This is called once at startup to produce the previous day's summary
    (no job queue required).
    """
    yesterday = iran_now() - timedelta(days=1)
    y_greg = yesterday.strftime("%Y-%m-%d")
    aggregated = []
    for fname in os.listdir(LOG_DIR):
        if fname.endswith(f"{y_greg}.txt"):
            path = os.path.join(LOG_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    aggregated.append(f"--- {fname} ---\n")
                    aggregated.append(f.read())
                    aggregated.append("\n\n")
            except Exception as e:
                print("Error reading log file", path, e)

    if aggregated:
        out_path = os.path.join(LOG_DIR, f"daily_log_{y_greg}.txt")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.writelines(aggregated)
            print("Daily aggregated log saved:", out_path)
        except Exception as e:
            print("Error writing daily aggregated log:", e)
    else:
        print("No logs found for", y_greg)

def get_message_type(message: Message) -> str:
    if message.text or message.caption and message.caption.strip() and not (
        message.photo or message.video or message.document or message.voice or message.audio
    ):
        # caption can exist on media — handle media separately below
        if message.text:
            return "متن"
    if message.photo:
        return "عکس"
    if message.video:
        return "ویدئو"
    if message.document:
        return "فایل"
    if message.audio:
        return "صوت"
    if message.voice:
        return "ویس"
    if message.sticker:
        return "استیکر"
    if message.video_note:
        return "وینوته"
    # if message has caption and a media type, prioritize media type
    if message.caption:
        if message.photo:
            return "عکس"
        if message.video:
            return "ویدئو"
        if message.document:
            return "فایل"
    return "سایر"

def build_message_link(chat, message_id: int) -> str:
    # public chat with username
    try:
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}/{message_id}"
        # supergroup/channel private: /c/<internal>/<message_id>
        if getattr(chat, "type", "") in ("supergroup", "channel"):
            internal = str(chat.id)
            if internal.startswith("-100"):
                internal_id = internal[4:]
            else:
                internal_id = internal.lstrip("-")
            return f"https://t.me/c/{internal_id}/{message_id}"
    except Exception:
        pass
    return "لینک ندارد"

# --- Main handler ---
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message:
        return

    chat = update.effective_chat
    user = update.effective_user

    chat_id = chat.id
    # Respect SOURCE_CHAT_IDS filter
    if SOURCE_CHAT_IDS != ["*"] and str(chat_id) not in SOURCE_CHAT_IDS:
        return

    # times
    dt_iran = iran_now()
    # Jalali date
    dt_j = jdatetime.datetime.fromgregorian(datetime=dt_iran)
    date_jalali = dt_j.strftime("%Y/%m/%d")
    time_str = dt_iran.strftime("%H:%M:%S")

    # message details
    msg_type = get_message_type(message)
    # client/via bot info
    client_info = getattr(message, "via_bot", None)
    if client_info:
        client_txt = f"@{client_info.username}" if getattr(client_info, "username", None) else str(client_info)
    else:
        client_txt = "نامعلوم"

    # reply info (user + preview)
    if message.reply_to_message:
        r = message.reply_to_message
        r_user = r.from_user.full_name if (r.from_user and getattr(r.from_user, "full_name", None)) else "نامشخص"
        # preview text if text else indicate non-text
        if r.text:
            preview = r.text if len(r.text) <= 120 else (r.text[:117] + "...")
        elif r.caption:
            preview = r.caption if len(r.caption) <= 120 else (r.caption[:117] + "...")
        else:
            preview = "📎 غیرمتنی"
        reply_info = f"{r_user} | «{preview}»"
    else:
        reply_info = "ندارد"

    # message link construction
    message_link = build_message_link(chat, message.message_id)

    # Build report text with exact requested structure.
    # Note: keep id on its own line (🆔)
    report_lines = [
        "📩 پیام از:",
        f"👤 نام: {user.full_name if user else 'نامشخص'}",
        f"🆔 آیدی: {user.id if user else 'نامشخص'}",
        f"🔗 یوزرنیم: @{user.username if (user and user.username) else 'ندارد'}",
        f"👥 چت/گروه: {chat.title or getattr(chat, 'full_name', None) or chat.id}",
        f"📌 نوع پیام: {msg_type}",
    ]

    # If text message: include text inside report and DO NOT forward original text.
    # If non-text: if it has caption, include caption in report; forward original media.
    text_block = ""
    if msg_type == "متن":
        body_text = message.text or ""
        # Put text as a separate "📩 متن:" block (even if empty)
        text_block = f"📩 متن:\n{body_text}"
        report_lines.append(text_block)
    else:
        # if non-text but has caption, include caption
        if getattr(message, "caption", None):
            report_lines.append(f"📩 متن:\n{message.caption}")

    # continue remaining fields
    report_lines.extend([
        f"📱 کلاینت: {client_txt}",
        f"↩️ ریپلای به: {reply_info}",
        f"🔗 لینک پیام: {message_link}",
        f"🕒 تاریخ شمسی: {date_jalali} | ساعت: {time_str}"
    ])

    report_text = "\n".join(report_lines)

    # Send report to all destinations
    for dest in DEST_CHAT_IDS:
        try:
            await context.bot.send_message(chat_id=dest, text=report_text)
        except Exception as e:
            print("Error sending report to", dest, e)

        # For non-text messages, forward (copy) the original message to destination
        if msg_type != "متن":
            try:
                await context.bot.copy_message(chat_id=dest, from_chat_id=chat_id, message_id=message.message_id)
            except Exception as e:
                print("Error forwarding message to", dest, e)

    # Save to per-chat daily log (UTF-8), filename uses safe chat name + YYYY-MM-DD (gregorian)
    safe_chat = safe_name(chat.title or getattr(chat, "full_name", None) or str(chat_id))
    file_date = dt_iran.strftime("%Y-%m-%d")  # for filename use gregorian Y-M-D
    log_filename = os.path.join(LOG_DIR, f"chat_{safe_chat}_{file_date}.txt")
    try:
        with open(log_filename, "a", encoding="utf-8") as lf:
            lf.write(report_text + "\n\n")
    except Exception as e:
        print("Error writing log:", log_filename, e)

# --- Entry point ---
if __name__ == "__main__":
    # At startup, create aggregated file of yesterday (no sending) so daily log is ready.
    try:
        save_daily_log()
    except Exception as e:
        print("save_daily_log error:", e)

    # Build and run the bot application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, forward_message))

    print("Bot started (async). Listening for messages...")
    app.run_polling()
