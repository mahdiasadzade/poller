import os
from fastapi import FastAPI
import uvicorn
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import asyncio

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEST_CHAT_IDS = [int(x) for x in os.getenv("DEST_CHAT_IDS", "").split(",")]
SOURCE_CHAT_IDS = os.getenv("SOURCE_CHAT_IDS", "*").split(",")

app = FastAPI()

# --- Route for Health Check / Web Service ---
@app.get("/")
def root():
    return {"status": "Bot running"}

# --- Telegram Bot Handler ---
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from_chat = update.effective_chat
    from_user = update.effective_user
    from_id = from_chat.id

    if SOURCE_CHAT_IDS != ["*"] and str(from_id) not in SOURCE_CHAT_IDS:
        return

    sender_info = f"📩 پیام از:\nنام: {from_user.full_name}\nآیدی: {from_user.id}\nگروه/چت: {from_chat.title or from_chat.full_name or from_chat.id}"

    for chat_id in DEST_CHAT_IDS:
        await context.bot.send_message(chat_id=chat_id, text=sender_info)
        await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_id,
            message_id=update.effective_message.message_id
        )

# --- Run Telegram Bot in Background ---
async def start_bot():
    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.ALL, forward_message))
    print("Bot started (async, Web Service compatible)")
    await bot_app.run_polling()

# Start Telegram bot in the background
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_bot())

# --- Run FastAPI Web Service ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
