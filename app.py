import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import google.generativeai as genai

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

SYSTEM_PROMPT = "Ти — оповідач. Відповідай українською."

def start(update, context):
    update.message.reply_text("🌙 Вітаю в Mystical Tales of Love!")

def handle_message(update, context):
    try:
        user_msg = update.message.text
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\nГравець: {user_msg}")
        update.message.reply_text(response.text[:4096])
    except Exception as e:
        update.message.reply_text("Вибач, сталася помилка. Спробуй ще раз.")

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return 'ok'

@app.route('/')
def index():
    return "Bot is running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)