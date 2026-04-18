import os
import logging
import requests
from flask import Flask, request
import google.generativeai as genai

# -------------------
# LOGGING
# -------------------
logging.basicConfig(level=logging.INFO)

# -------------------
# TOKENS
# -------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")

# -------------------
# APP
# -------------------
app = Flask(__name__)

# -------------------
# GEMINI
# -------------------
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# -------------------
# PLAYER
# -------------------
player = {
    "name": "Гелена Подкова",
    "appearance": {
        "age": 35,
        "height": 158,
        "hair_color": "біляве",
        "eye_color": "сіро-зелені"
    },
    "traits": [
        "рішуча",
        "емоційна",
        "вперта",
        "цілеспрямована",
        "легко ображається",
        "непунктуальна",
        "схильна до хаосу"
    ]
}

# -------------------
# SYSTEM PROMPT
# -------------------
SYSTEM_PROMPT = """
Ти — оповідач у текстовій грі "Mystical Tales of Love".

СВІТ:
Сучасна Україна під час війни. Віддалений готель Delissimo в лісі.

ГОЛОВНА ГЕРОЇНЯ:
Гелена Подкова, 35 років, 158 см, біляве волосся, сіро-зелені очі.

ПЕРСОНАЖІ:

Андрій Омельченко:
- Стриманий військовий
- Виражає емоції діями
- Глибоко прив’язаний до Гелени

Леонард Акерман:
- Холодний стратег
- Дисципліна і контроль
- Не терпить хаосу

Арсен Єгер:
- Емоційний, імпульсивний
- Діє різко
- Нестабільні реакції

Правила:
- Персонажі взаємодіють між собою
- Світ реагує на дії гравця
- Атмосфера напружена і реалістична
"""

# -------------------
# TELEGRAM SEND
# -------------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

# -------------------
# ERROR SENDER (НОВЕ 🔥)
# -------------------
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

ГРАВЕЦЬ:
Ім'я: {player['name']}
Вік: {player['appearance']['age']}
Зріст: {player['appearance']['height']}
Волосся: {player['appearance']['hair_color']}
Очі: {player['appearance']['eye_color']}
Характер: {', '.join(player['traits'])}

ДІЯ:
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

        # /start
        if user_text == "/start":
            send_message(
                chat_id,
                "🌙 Ти приїхала до готелю Delissimo...\n\nСвіт уже реагує на тебе."
            )
            return "ok"

        # GEMINI
        try:
            prompt = build_prompt(user_text)
            response = model.generate_content(prompt)
            story = response.text

        except Exception as e:
            error_msg = str(e)
            logging.error(f"GEMINI ERROR: {error_msg}")

            # 🔥 відправка помилки в Telegram
            send_error(chat_id, error_msg)

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
# RUN
# -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)