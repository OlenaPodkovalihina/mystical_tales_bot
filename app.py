import os
import logging
from flask import Flask, request
from telegram import Bot, Update
import google.generativeai as genai

# Налаштування логування
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    logging.error("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")
    raise ValueError("Missing tokens")

bot = Bot(token=TOKEN)
app = Flask(__name__)

# Налаштування Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')  # ВИКОРИСТОВУЄМО ПРАВИЛЬНУ МОДЕЛЬ!

SYSTEM_PROMPT = "Ти — оповідач у грі 'Mystical Tales of Love'. Відповідай українською, атмосферно."

# ОБРОБНИК WEBHOOK (БЕЗ Dispatcher)
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        # Отримуємо оновлення від Telegram
        update = Update.de_json(request.get_json(), bot)
        
        if update and update.message:
            chat_id = update.message.chat_id
            user_text = update.message.text
            
            # Обробка команди /start
            if user_text == '/start':
                bot.send_message(chat_id=chat_id, text="🌙 Ласкаво просимо до *Mystical Tales of Love*!\n\nНапиши щось, і я розпочну історію...", parse_mode='Markdown')
                return 'ok'
            
            # Обробка звичайних текстових повідомлень
            response = model.generate_content(f"{SYSTEM_PROMPT}\n\nГравець: {user_text}")
            bot.send_message(chat_id=chat_id, text=response.text[:4096])
            
    except Exception as e:
        logging.error(f"Помилка в webhook: {e}")
    
    return 'ok'

@app.route('/')
def index():
    return "Bot is running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)