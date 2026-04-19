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

PLAYER = {
    "name": "Гелена Подкова",
    "age": 35,
    "gender": "жінка",
    "appearance": {
        "height": "158 см",
        "hair": "біляве, довге",
        "eyes": "сіро-зелені",
        "body": "струнка"
    },
    "personality": [
        "рішуча",
        "емоційна",
        "вперта",
        "цілеспрямована",
        "легко ображається",
        "схильна до хаосу",
        "іноді ігнорує правила"
    ],
    "profession": "доцент",
    "specialty": "комп’ютерні науки",
    "likes": [
        "містика",
        "хоррор",
        "коти",
        "фільми жахів",
        "трилери",
        "жовтий колір",
        "їжа",
        "комп’ютерні ігри"
    ],
    "dislikes": [
        "мелодрами",
        "рутина",
        "чіткий розпорядок",
        "бути голодною",
        "мити посуд",
        "отримувати вказівки"
    ],
    "abilities": [
        "екстрасенсорні здібності",
        "бачить майбутнє (спонтанно)",
        "віщі сни",
        "бачить сутності"
    ]
}


PLAYER_IMG = "https://drive.google.com/uc?export=view&id=1rsO3DJhpfBgGu2l9oS2MLCqhwxnyJdYj"


# -------------------
# TELEGRAM HELPERS
# -------------------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": text
    })

def send_photo(chat_id, photo_url, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    requests.post(url, json={
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption
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
    player_text = f"""
ГРАВЕЦЬ:
{PLAYER['name']} ({PLAYER['age']} років, жінка)

Зовнішність:
- зріст: {PLAYER['appearance']['height']}
- волосся: {PLAYER['appearance']['hair']}
- очі: {PLAYER['appearance']['eyes']}
- статура: {PLAYER['appearance']['body']}

Характер:
{", ".join(PLAYER['personality'])}

Професія:
{PLAYER['profession']} ({PLAYER['specialty']})

Любить:
{", ".join(PLAYER['likes'])}

Не любить:
{", ".join(PLAYER['dislikes'])}

Особливості:
{", ".join(PLAYER['abilities'])}
"""

    return f"""
{SYSTEM_PROMPT}

{player_text}

ПРАВИЛА:
- Завжди використовуй жіночий рід щодо гравця
- Не змінюй її характер
- Пам’ятай її особливості

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
            send_photo(chat_id, PLAYER_IMG, "Це ти.")
            send_message(chat_id, "🌙 Ти приїхала до готелю Delissimo...\nЩось у цьому місці не так.")
            return "ok"

        # GEMINI CALL
        try:
            prompt = build_prompt(user_text)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
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