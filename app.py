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
# TABLE
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
# FLASK APP
# -------------------
app = Flask(__name__)


def get_session(chat_id):
    chat_id = str(chat_id)
    session = load_session(chat_id)
    updated = False  # Прапорець, який покаже, чи міняли ми щось

    # 1. Якщо сесії взагалі немає
    if not session:
        session = {
            "history": [],
            "state": {"location": "дорога до готелю"},
            "characters": {
                "leonard": {"met": False, "trust": 0}
            },
            "branch": "Тіні минулого",
            "active_character": "leonard"
        }
        updated = True
    else:
        # 2. Перевіряємо стару сесію на наявність усіх полів (валідація)
        if "history" not in session:
            session["history"] = []
            updated = True
        if "characters" not in session:
            session["characters"] = {"leonard": {"met": False, "trust": 0}}
            updated = True
        if "state" not in session:
            session["state"] = {"location": "дорога до готелю"}
            updated = True
        if "active_character" not in session:
            session["active_character"] = "leonard"
            updated = True

    # 3. Зберігаємо ТІЛЬКИ якщо були зміни в структурі
    if updated:
        logging.info(f"Оновлення структури сесії для {chat_id}")
        save_session(chat_id, session)
    
    return session

# -------------------
# GEMINI CLIENT (NEW SDK)
# -------------------
client = genai.Client(api_key=GEMINI_KEY)

models = client.models.list()
print([m.name for m in models])

# 1. Виносимо конфіг окремо, щоб не дублювати
GENERATION_CONFIG = {
    "temperature": 0.85,
}

# Твій список моделей (я додав сюди Pro, бо для дослідника це важливо)
MODELS = [

    "gemini-2.5-flash",  # Швидка і сучасна
    "gemini-2.0-flash",   # Надійний запасний варіант
    "gemini-2.5-pro",    # Найрозумніша — для душі та драми
]

def generate_with_fallback(prompt, leonard_trust_value):
    # МИ НЕ СТВОРЮЄМО НОВУ system_instruction ТУТ!
    # Замість цього ми просто додаємо короткий технічний опис стану
    state = get_trust_state(leonard_trust_value)
    
    # Використовуємо твій великий prompt як основу, 
    # а в інструкцію виносимо ТІЛЬКИ динамічні емоції
    dynamic_context = f"Рівень довіри: {leonard_trust_value}. Тон: {state['tone']}. Внутрішній режим: {state['mode']}."

    for model_id in MODELS:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt, # Твій великий промпт іде сюди повністю
                config={
                    "system_instruction": f"Ти — Майор Леонард. Твій стан зараз: {dynamic_context}. Завжди пиши думки в дужках ().", 
                    "temperature": GENERATION_CONFIG["temperature"],
                    "max_output_tokens": GENERATION_CONFIG["max_output_tokens"],
                }
            )
            return response.text
        except Exception as e:
            logging.warning(f"{model_id} failed: {e}")

    return "Зв'язок розірвано..."

# -------------------
# SYSTEM PROMPT
# -------------------
SYSTEM_PROMPT = """
Ти — оповідач інтерактивної текстової гри.
"""
WORLD = """
СВІТ:

- Реальність: сучасна Україна під час війни
- Атмосфера: напруга, небезпека, невідомість
- У світі можуть існувати:
    - військові
    - цивільні
    - покинуті місця
    - аномальні явища

ПРАВИЛА СВІТУ:
- персонажі поводяться реалістично
- небезпека завжди присутня
- рішення мають наслідки
- довіра між людьми формується повільно
- містика існує, але не пояснюється одразу

ЛОКАЦІЇ МОЖУТЬ ЗМІНЮВАТИСЯ:
- готель
- місто
- ліс
- кладовище
- військова база

СЮЖЕТ ГІЛКИ "ТІНІ МИНУЛОГО":
- 20 років тому в готелі Delissimo були вбиті всі мешканці
- вбивцю не знайшли
- готель закрили
- нещодавно його відкрили після ремонту
- щось у цьому місці залишилось

ЗАВДАННЯ:
- розібратися, що сталося
- знайти правду
- вижити

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
- статура: жилава
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
- якщо довіряє, то захищає до кінця

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
- якщо відчуває симпатію, то це проявляється як контроль, захист і жорсткі рішення замість слів
- довіра Леонарда впливає на його поведінку

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


# =========================
# 🧠 LEONARD AI CORE
# =========================

TRUST_STATES = [
    {"min": -999, "max": -2, "mode": "hostile", "tone": "холодний, різкий, відсторонений"},
    {"min": -1, "max": 5, "mode": "neutral", "tone": "стриманий, професійний"},
    {"min": 5, "max": 10, "mode": "curious", "tone": "уважний, більше взаємодії"},
    {"min": 10, "max": 15, "mode": "bonded", "tone": "захисний, інколи м’який, приховано емоційний"},
    {"min": 15, "max": 20, "mode": "sympathy", "tone": "рідкісні погляди, спостерігає здалеку, провокує на емоції, злегка піддражнює"},
    {"min": 20, "max": 25, "mode": "inlove", "tone": "захищає, але грубо, без ніжності, шукає привід бути поруч, ревнує"},
    {"min": 25, "max": 999, "mode": "relationships", "tone": "втрачає контроль, діє імпульсивно, поцілунки, близкість"},
]


def get_trust_state(trust: int):
    for state in TRUST_STATES:
        if state["min"] <= trust <= state["max"]:
            return state
    return TRUST_STATES[1]


def update_leonard_trust(leonard, user_text: str):
    text = user_text.lower()

    # 🔵 довіра через співпрацю
    if any(w in text for w in ["допомогти", "разом", "довіряю", "залишаюсь", "дякую", "ти мав рацію", "в безпеці", "ти захистив мене"]):
        leonard["trust"] += 1

    # 🟡 виклик = повага (як ти і хотіла)
    if any(w in text for w in ["я сама", "не командуй", "ти помиляєшся", "я можу", "я впораюся"]):
        leonard["trust"] += 1

    # 🔴 відштовхування
    if any(w in text for w in ["йди", "відстань", "не чіпай", "ти повинен", "твоя помилка", "твоя вина"]):
        leonard["trust"] -= 2

    # 🟡 виклик = закоханість
    if any(w in text for w in ["я тебе не боюся", "я не відступлю", "я не здаюся", "ти милий", "ти дурень", "ти теплий", "ти врятував"]):    
        leonard["trust"] += 3


def generate_leonard_thought(leonard, player_text: str):
    trust_state = get_trust_state(leonard["trust"])

    if trust_state["mode"] == "hostile":
        return "(Контроль втрачати не можна.)"

    if trust_state["mode"] == "neutral":
        return "(Спостерігаю. Поки нічого зайвого.)"

    if trust_state["mode"] == "curious":
        return "(Вона не реагує як більшість. Це цікаво.)"

    if trust_state["mode"] == "bonded":
        return "(Вона тримається. Це… добре.)"

    if trust_state["mode"] == "sympathy":
        return "(Вона привернула мою увагу.)"

    if trust_state["mode"] == "inlove":
        return "(Я закохуюся?... Це неможливо.)"

    if trust_state["mode"] == "relationships":
        return "(Вона моя)"

def get_leonard_behavior(leonard):
    return get_trust_state(leonard["trust"])["tone"]


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

def send_main_menu(chat_id):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": "Обери дію:",
        "reply_markup": {
            "keyboard": [
                ["💾 Зберегти історію"]
            ],
            "resize_keyboard": True
        }
    })

def send_error(chat_id, error_text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": chat_id,
        "text": f"⚠️ ERROR:\n{error_text}"
    })

# -------------------
# LOAD AND SAVE
# -------------------
def load_session(chat_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT data FROM sessions WHERE chat_id = %s", (str(chat_id),))
    row = cur.fetchone()

    conn.close()

    if row:
        data = row[0]
        # Якщо база повернула рядок замість об'єкта — перетворюємо
        if isinstance(data, str):
            try:
                return json.loads(data)
            except:
                return None
        return data  # Якщо це вже dict (словник), повертаємо як є
    return None


def save_session(chat_id, session_data):
    conn = get_db()
    cur = conn.cursor()

    serialized_data = json.dumps(session_data)

    cur.execute("""
    INSERT INTO sessions (chat_id, data)
    VALUES (%s, %s)
    ON CONFLICT (chat_id)
    DO UPDATE SET data = EXCLUDED.data
    """, (str(chat_id), serialized_data))

    conn.commit()
    conn.close()

# -------------------
# PROMPT BUILDER
# -------------------
def build_prompt(user_text, session):
    history_text = "\n".join(
        [f"{m['role']}: {m['text']}" for m in session["history"][-8:]]
    )

    leonard = session["characters"]["leonard"]

    leonard_thought = generate_leonard_thought(leonard, user_text)
    behavior_tone = get_leonard_behavior(leonard)
    branch = session.get("branch", "Тіні минулого") 
    active_character = session.get("active_character", "leonard")  

    return f"""
{SYSTEM_PROMPT}
{WORLD}

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
{CHARACTERS['leonard']['description']}

АКТИВНИЙ ПЕРСОНАЖ:
Леонард Акерман
- відповіді повинні відображати його характер, стиль мислення і поведінку
- його внутрішній стан впливає на тон сцени

СТАН ГРИ:
- локація: {session['state']['location']}
- Леонард зустрінутий: {leonard['met']}
- рівень довіри: {leonard['trust']}

ПОВЕДІНКА ЛЕОНАРДА:
- тон: {behavior_tone}

ВНУТРІШНІ ДУМКИ ЛЕОНАРДА (НЕ ДЛЯ ГРАВЦЯ, АЛЕ МОЖУТЬ ІНОДІ ПОЯВЛЯТИСЯ В ТЕКСТІ):
{leonard_thought}

ІСТОРІЯ:
{history_text}

СЮЖЕТ:
- якщо Леонард ще не зустрінутий, то введи його природно
- перша зустріч напружена
- він не відкривається одразу

ПРАВИЛА:
- Завжди використовуй жіночий рід щодо гравця
- Не змінюй її характер
- Памятай її особливості
- памятай події
- не ламай характер персонажів
- показуй думки Леонарда в дужках ()
- думки не завжди озвучуються вголос

ДІЯ ГРАВЦЯ:
{user_text}

ФОРМАТ ВІДПОВІДІ:
1. Текст від імені Леонарда (думки в дужках + пряма мова).
2. В самому кінці повідомлення обов'язково виведи технічну інформацію:

Стан гри:
Локація: {session['state']['location']}
Рівень довіри: {leonard['trust']}
Статус Леонарда: {behavior_tone}
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
            session = get_session(chat_id)
            save_session(chat_id, session)

            send_photo(chat_id, PLAYER_IMG, "Це ти.")
            send_message(chat_id, """
               Я приїхала в містечко Ясіня у відпустку.

               Дорога була виснажливою — майже добу в поїзді.
               Потім ще дві години очікування автобуса.

               Від автовокзалу дорога йде вздовж кількох магазинів.
               Далі — зупинка.

               Тепер мені потрібно чекати ще один автобус, який зупиняється біля готелю Delissimo.

               Йти пішки — не варіант. Сумка важка.

               Навколо нікого.
               Магазини вже зачинені.
               Ліс підступає майже впритул.

               І починається дощ.

               Я втомлена.
               Голодна.
               І замерзла.
               """)


            send_main_menu(chat_id) 
            return "ok"

        # 💾 SAVE COMMAND
        if user_text == "💾 Зберегти історію":
            session = get_session(chat_id)  # важливо!
            save_session(chat_id, session)
            send_message(chat_id, "💾 Історію збережено.")
            return "ok"

        # GEMINI CALL
        try:
            session = get_session(chat_id)
            prompt = build_prompt(user_text, session)

            # Отримуємо число довіри з сесії
            current_trust = session["characters"]["leonard"]["trust"]

            # Передаємо обидва аргументи у функцію
            story = generate_with_fallback(prompt, current_trust)
            
            # 💾 ПАМ’ЯТЬ
            session["history"].append({"role": "user", "text": user_text})
            session["history"].append({"role": "ai", "text": story})

            # 🎭 ЛОГІКА ЛЕОНАРДА
            leonard = session["characters"]["leonard"]

            # перша поява
            if not leonard["met"] and "Леонард" in story:
                leonard["met"] = True
                send_photo(chat_id, LEONARD_IMG, "Перед тобою з’являється чоловік...")

            # система довіри
            if leonard["met"]:
                update_leonard_trust(leonard, user_text)

            # 💾 SAVE
            save_session(chat_id, session)

            # 📤 SEND
            send_message(chat_id, story[:4096])

        except Exception as e:
            logging.error(f"GEMINI ERROR: {e}")
            send_error(chat_id, str(e))
            return "ok"


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