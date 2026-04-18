import os
import logging
import requests
from flask import Flask, request
from google import genai

# -------------------
# LOGGING
# -------------------
logging.basicConfig(level=logging.INFO)

# -------------------
# ENV VARIABLES
# -------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")

# -------------------
# FLASK APP
# -------------------
app = Flask(__name__)

# -------------------
# GEMINI CLIENT (NEW SDK)
# -------------------
client = genai.Client(api_key=GEMINI_KEY)

models = client.models.list()
print([m.name for m in models])

# -------------------
# SYSTEM PROMPT
# -------------------
SYSTEM_PROMPT = """
Ти — оповідач інтерактивної текстової гри.

СВІТ:
Сучасна Україна під час війни.
Віддалений готель Delissimo у лісі.

СТИЛЬ:
- похмура атмосфера
- психологічна напруга
- реалістичні реакції персонажів
- розвиток сюжету через вибір гравця
"""

# -------------------
# TELEGRAM HELPERS
# -------------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })


def send_error(chat_id, error_text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": f"⚠️ ERROR:\n{error_text}"
    })

# -------------------
# PROMPT BUILDER
# -------------------
def build_prompt(user_text):
    return f"""
{SYSTEM_PROMPT}

ДІЯ ГРАВЦЯ:
{user_text}
"""

# -------------------
# WEBHOOK
# -------------------
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()

        if "message" not in data:
            return "ok"

        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        # START COMMAND
        if user_text == "/start":
            send_message(chat_id, "🌙 Ти приїхала до готелю Delissimo...\nЩось у цьому місці не так.")
            return "ok"

        # GEMINI CALL
        try:
            prompt = build_prompt(user_text)

            response = client.models.generate_content(
                model="gemini-1.5-pro",
                contents=prompt
            )

            story = response.text or "..."

        except Exception as e:
            logging.error(f"GEMINI ERROR: {e}")
            send_error(chat_id, str(e))
            story = "Магія на мить зникла..."

        send_message(chat_id, story[:4096])

    except Exception as e:
        logging.error(f"WEBHOOK ERROR: {e}")

    return "ok"

# -------------------
# HEALTH CHECK
# -------------------
@app.route("/")
def index():
    return "Bot is running"

# -------------------
# RUN SERVER
# -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)