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

sessions = {}

def get_session(chat_id):
    if chat_id not in sessions:
        sessions[chat_id] = {
            "history": [],
            "state": {
                "location": "дорога до готелю"
            }
        }
    return sessions[chat_id]

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

CHARACTERS = {
    "leonard": {
        "name": "Леонард Акерман",
        "age": 34,
        "met": False,
        "trust": 0,

        "description": f"""
Леонард Акерман, 34 роки.

Військове звання: майор Збройних сил України

Зовнішність:
- зріст: 162 см
- волосся: чорне, коротке
- очі: сіро-блакитні
- статура: жилава, м'язиста
- особливість: шрам на лівій щоці

Характер:
- дисциплінований, холодний, раціональний
- не терпить слабкість і хаос
- говорить коротко і по суті

Поведінка:
- у стресі: ще холодніший, діє швидко
- у стосунках: контролює дистанцію, захищає діями
- емоції приховує

Особливість:
- довіра = рідкість
- якщо довіряє — захищає до кінця

Навички:
- управління FPV-дронами
- швидке прийняття рішень
- рукопашний бій

Любить:
- чорний чай без цукру
- чистота і порядок
- точність

Не любить:
- хаос
- балакучість
- виправдання
- непунктуальність
- жалість до себе
- марнування часу
- кава

Стосунки:
- контролює дистанцію, не дозволяє собі слабкості
- якщо прив’язується — це проявляється як контроль, захист і жорсткі рішення замість слів

Бекграунд:
- виріс сиротою
- усиновлений у Німеччині
- повернувся в Україну у 2022
- минуле приховує
"""
    }
}

PLAYER_IMG = "https://drive.google.com/uc?export=view&id=1rsO3DJhpfBgGu2l9oS2MLCqhwxnyJdYj"
LEONARD_IMG = "https://drive.google.com/uc?export=view&id=1_md3nAXLV5f08ohqHKOwuAEn8MNb_5W9"

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
def build_prompt(user_text, session):
    history_text = "\n".join(
        [f"{m['role']}: {m['text']}" for m in session["history"][-6:]]
    )

    leonard = CHARACTERS["leonard"]

    return f"""
{SYSTEM_PROMPT}

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

ПЕРСОНАЖ:
{leonard['description']}

СТАН ГРИ:
- локація: {session['state']['location']}
- Леонард зустрінутий: {leonard['met']}
- рівень довіри: {leonard['trust']}

ІСТОРІЯ:
{history_text}

СЮЖЕТ:
- якщо Леонард ще не зустрінутий - введи його природно
- перша зустріч напружена
- він не відкривається одразу

ПРАВИЛА:
- Завжди використовуй жіночий рід щодо гравця
- Не змінюй її характер
- Пам’ятай її особливості
- пам’ятай події
- не ламай характер персонажів

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
            session = get_session(chat_id)
            prompt = build_prompt(user_text, session)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )

            story = response.text or "..."
            
            # 💾 ПАМ’ЯТЬ
            session["history"].append({"role": "user", "text": user_text})
            session["history"].append({"role": "ai", "text": story})

            # 🎭 ЛОГІКА ЛЕОНАРДА
            leonard = CHARACTERS["leonard"]

            # перша поява
            if not leonard["met"] and "Леонард" in story:
                leonard["met"] = True
                send_photo(chat_id, LEONARD_IMG, "Перед тобою з’являється чоловік...")

            # система довіри
            if leonard["met"]:
                text = user_text.lower()

                if any(word in text for word in ["допомогти", "разом", "довіряю"]):
                    leonard["trust"] += 1

                if any(word in text for word in ["йди", "відстань", "не чіпай"]):
                    leonard["trust"] -= 1

            # 📤 ВІДПРАВКА
            send_message(chat_id, story[:4096])


        except Exception as e:
            logging.error(f"GEMINI ERROR: {e}")
            send_error(chat_id, str(e))
            story = "Магія на мить зникла..."


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