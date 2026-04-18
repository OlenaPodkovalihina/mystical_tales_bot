import os
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """Ти — оповідач у грі "Mystical Tales of Love". Відповідай українською, атмосферно, таємничо."""

async def start(update: Update, context):
    await update.message.reply_text("🌙 Вітаю в Mystical Tales of Love! Напиши щось, і я розпочну історію.")

async def handle_message(update: Update, context):
    user_msg = update.message.text
    response = model.generate_content(f"{SYSTEM_PROMPT}\n\nГравець: {user_msg}")
    await update.message.reply_text(response.text[:4096])

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))).start()
    main()