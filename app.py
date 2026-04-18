import os
import logging
from flask import Flask, request
from telegram import Bot, Update
import google.generativeai as genai

# === НАЛАШТУВАННЯ ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")

bot = Bot(token=TOKEN)
app = Flask(__name__)

genai.configure(api_key=GEMINI_KEY)
# ВИПРАВЛЕНО: замінено на актуальну модель
model = genai.GenerativeModel('gemini-2.0-flash-exp')

SYSTEM_PROMPT = """Ти — оповідач у грі "Mystical Tales of Love".
Відповідай українською, атмосферно, таємничо, з легким відтінком меланхолії."""

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(), bot)
        if update and update.message:
            user_msg = update.message.text
            chat_id = update.message.chat_id
            response = model.generate_content(f"{SYSTEM_PROMPT}\n\nГравець: {user_msg}")
            bot.send_message(chat_id=chat_id, text=response.text[:4096])
    except Exception as e:
        logging.error(f"Помилка: {e}")
    return 'ok'

@app.route('/')
def index():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)