import os
import logging
import requests
from flask import Flask, request
import google.generativeai as genai

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)

# ---------------- ENV ----------------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN:
    raise ValueError("Missing TELEGRAM_TOKEN")
if not GEMINI_KEY:
    raise ValueError("Missing GEMINI_API_KEY")

# ---------------- APP ----------------
app = Flask(__name__)

# ---------------- GEMINI ----------------
genai.configure(api_key=GEMINI_KEY)

# 🔥 СТАБІЛЬНА модель (якщо одна впаде — пробуємо іншу)
MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro"
]

SYSTEM_PROMPT = (
    "Ти — оповідач у грі 'Mystical Tales of Love'. "
    "Твоя задача — створювати атмосферні, короткі історії українською."
)

def generate_text(prompt: str):
    """Спроба викликати Gemini з fallback моделями"""
    for m in MODELS:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)

            if response and response.text:
                return response.text

        except Exception as e:
            logging.warning(f"Model {m} failed: {e}")

    return None  # якщо все впало

# ---------------- TELEGRAM ----------------
def send_message(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
    except Exception as e:
        logging.error(f"Telegram send error: {e}")

# ---------------- WEBHOOK ----------------
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return "ok"

        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        # /start
        if text == "/start":
            send_message(
                chat_id,
                "🌙 Ласкаво просимо до *Mystical Tales of Love*!\n\n"
                "Напиши щось — і я створю історію ✨"
            )
            return "ok"

        # генерація
        prompt = f"{SYSTEM_PROMPT}\n\nГравець: {text}"
        reply = generate_text(prompt)

        # 🔥 FALLBACK (якщо Gemini впав)
        if not reply:
            reply = (
                "🌙 Магія на мить зникла...\n"
                "Але ти все ще стоїш у темному коридорі старого готелю."
            )

        send_message(chat_id, reply[:4096])

    except Exception as e:
        logging.exception("Webhook error")

    return "ok"

# ---------------- HEALTH CHECK ----------------
@app.route("/")
def index():
    return "Bot is running"

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)