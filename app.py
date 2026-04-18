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
# WORLD STATE (простий “движок напруги”)
# -------------------
world_state = {
    "tension": 10,   # загальна напруга в готелі
    "risk": 5        # ризик подій
}

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
        "непунктуальна",
        "легко ображається"
    ]
}

# -------------------
# SYSTEM PROMPT (персонажі тепер тут)
# -------------------
SYSTEM_PROMPT = """
Ти — оповідач у текстовій грі "Mystical Tales of Love".

СВІТ:
Сучасна Україна під час війни. Віддалений готель Delissimo в лісі.

ГОЛОВНА ГЕРОЇНЯ:
Гелена Подкова, 35 років, 158 см, біляве волосся, сіро-зелені очі.
Характер: рішуча, емоційна, вперта, непунктуальна, легко ображається.

ПЕРСОНАЖІ:

Андрій Омельченко:
- Стриманий військовий
- Діє через вчинки, не слова
- Приховано прив’язаний до Гелени

Леонард Акерман:
- Холодний стратег
- Контроль, дисципліна, логіка
- Не терпить хаосу

Арсен Єгер:
- Емоційний, вибуховий
- Ненавидить контроль
- Діє імпульсивно

ПРАВИЛА:
- Персонажі взаємодіють між собою
- Світ реагує на дії гравця
- Атмосфера напружена і жива
"""

# -------------------
# TELEGRAM SEND
# -------------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})

# -------------------
# WORLD REACTION ENGINE (гібрид)
# -------------------
def world_tick(user_text):
    text = user_text.lower()
    reactions = []

    # напруга росте від емоційних дій
    if any(w in text for w in ["боюсь", "ні", "піти", "не хочу"]):
        world_state["tension"] += 2
        reactions.append("Андрій стає уважнішим до тебе.")

    if "?" in text:
        world_state["risk"] += 1
        reactions.append("Леонард оцінює ситуацію холодно.")

    if any(w in text for w in ["сміюся", "жарт", "провок"]):
        world_state["tension"] += 3
        reactions.append("Арсен реагує різкіше, ніж очікувалось.")

    # загальна атмосфера
    if world_state["tension"] > 20:
        reactions.append("У повітрі відчувається напруга.")

    if not reactions:
        reactions.append("Delissimo залишається підозріло тихим.")

    return "\n".join(reactions)

# -------------------
# PROMPT BUILDER
# -------------------
def build_prompt(user_text):
    return f"""
{SYSTEM_PROMPT}

СТАН СВІТУ:
Напруга: {world_state['tension']}
Ризик подій: {world_state['risk']}

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

        # START
        if user_text == "/start":
            send_message(chat_id,
                "🌙 Ти приїхала до Delissimo...\n\nСвіт реагує на тебе вже зараз."
            )
            return "ok"

        # GEMINI STORY
        try:
            prompt = build_prompt(user_text)
            response = model.generate_content(prompt)
            story = response.text
        except Exception as e:
            logging.error(e)
            story = "Магія на мить зникла..."

        # WORLD LAYER
        world = world_tick(user_text)

        final = f"{story}\n\n{world}"

        send_message(chat_id, final[:4096])

    except Exception as e:
        logging.error(f"Webhook error: {e}")

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