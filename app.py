import os
import logging
import requests
from flask import Flask, request
from google import genai
import json
import psycopg2

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
# DB
# -------------------
def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        chat_id TEXT PRIMARY KEY,
        data JSONB
    )
    """)

    conn.commit()
    conn.close()


init_db()

# -------------------
# FLASK
# -------------------
app = Flask(__name__)

# -------------------
# LOAD / SAVE
# -------------------
def load_session(chat_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT data FROM sessions WHERE chat_id = %s", (chat_id,))
    row = cur.fetchone()

    conn.close()

    if row:
        return row[0]

    return None


def save_session(chat_id, session_data):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO sessions (chat_id, data)
    VALUES (%s, %s)
    ON CONFLICT (chat_id)
    DO UPDATE SET data = EXCLUDED.data
    """, (chat_id, json.dumps(session_data)))

    conn.commit()
    conn.close()


def get_session(chat_id):
    chat_id = str(chat_id)

    session = load_session(chat_id)

    if session:
        return session

    session = {
        "history": [],
        "state": {
            "location": "дорога до готелю"
        },
        "characters": {
            "leonard": {
                "met": False,
                "trust": 0
            }
        },
        "branch": "Тіні минулого",
        "active_character": "leonard"
    }

    save_session(chat_id, session)
    return session


# -------------------
# GEMINI
# -------------------
client = genai.Client(api_key=GEMINI_KEY)

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest"
]


def generate_with_fallback(prompt):
    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logging.warning(f"{model} failed: {e}")

    return "Магія зникла..."


# -------------------
# WORLD
# -------------------
WORLD = """
СВІТ:

- Реальність: сучасна Україна під час війни
- Атмосфера: напруга, небезпека, невідомість

ПРАВИЛА:
- персонажі реалістичні
- рішення мають наслідки
- довіра формується повільно
- містика існує, але не пояснюється одразу

ЛОКАЦІЇ:
- готель
- місто
- ліс
- кладовище
- військова база

СЮЖЕТ "ТІНІ МИНУЛОГО":
- 20 років тому в готелі Delissimo були вбиті всі мешканці
- вбивцю не знайшли
- готель закрили
- нещодавно відкрили знову
- щось залишилось
"""

# -------------------
# SYSTEM
# -------------------
SYSTEM_PROMPT = """
Ти — оповідач інтерактивної текстової гри.
"""

# -------------------
# PLAYER
# -------------------
PLAYER = {
    "name": "Гелена Подкова",
    "age": 35,
    "appearance": {
        "height": "158 см",
        "hair": "біляве, довге",
        "eyes": "сіро-зелені",
        "body": "струнка"
    }
}

# -------------------
# TELEGRAM
# -------------------
def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text}
    )


def send_photo(chat_id, photo_url, caption=""):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
        json={"chat_id": chat_id, "photo": photo_url, "caption": caption}
    )


def send_main_menu(chat_id):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "Обери дію:",
            "reply_markup": {
                "keyboard": [["💾 Зберегти історію"]],
                "resize_keyboard": True
            }
        }
    )

# -------------------
# PROMPT
# -------------------
def build_prompt(user_text, session):
    history_text = "\n".join(
        [f"{m['role']}: {m['text']}" for m in session["history"][-6:]]
    )

    return f"""
{SYSTEM_PROMPT}

{WORLD}

ГРАВЕЦЬ:
{PLAYER['name']} ({PLAYER['age']} років)

ІСТОРІЯ:
{history_text}

ДІЯ:
{user_text}
"""


# -------------------
# WEBHOOK
# -------------------
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    # START
    if user_text == "/start":
        session = get_session(chat_id)
        save_session(chat_id, session)

        send_message(chat_id, "Ти приїхала до готелю Delissimo...")
        send_main_menu(chat_id)
        return "ok"

    # SAVE BUTTON
    if user_text == "💾 Зберегти історію":
        session = get_session(chat_id)
        save_session(chat_id, session)
        send_message(chat_id, "Історію збережено.")
        return "ok"

    # AI
    session = get_session(chat_id)
    prompt = build_prompt(user_text, session)

    story = generate_with_fallback(prompt)

    session["history"].append({"role": "user", "text": user_text})
    session["history"].append({"role": "ai", "text": story})

    save_session(chat_id, session)

    send_message(chat_id, story[:4096])

    return "ok"


# -------------------
# RUN
# -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)