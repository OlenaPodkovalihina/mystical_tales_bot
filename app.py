import os
import logging
import requests
from flask import Flask, request
import google.generativeai as genai

# Логування
logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    logging.error("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")
    raise ValueError("Missing tokens")

app = Flask(__name__)

# Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

SYSTEM_PROMPT = "Ти — оповідач у грі 'Mystical Tales of Love'. Відповідай українською, атмосферно."

# Функція відправки повідомлення
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
    except Exception as e:
        logging.error(f"Помилка відправки: {e}")

# WEBHOOK
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    try:
        data = request.get_json()

        if "message" not in data:
            return 'ok'

        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        # /start
        if user_text == "/start":
            send_message(chat_id,
                "🌙 Ласкаво просимо до *Mystical Tales of Love*!\n\n"
                "Напиши щось, і я розпочну історію..."
            )
            return 'ok'

        # Генерація відповіді
        try:
            response = model.generate_content(
                f"{SYSTEM_PROMPT}\n\nГравець: {user_text}"
            )
            text = response.text if response.text else "..."
        except Exception as e:
            logging.error(f"Gemini помилка: {e}")
            text = "⚠️ Сталася помилка при генерації історії."

        send_message(chat_id, text[:4096])

    except Exception as e:
        logging.error(f"Помилка в webhook: {e}")

    return 'ok'

# Перевірка сервера
@app.route('/')
def index():
    return "Bot is running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)