import os
import asyncio
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# === НАЛАШТУВАННЯ ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")

bot = Bot(token=TOKEN)
app = Flask(__name__)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# === ТВІЙ ПЕРСОНАЖ ===
SYSTEM_PROMPT = """Ти — оповідач у грі "Mystical Tales of Love".
Ти ведеш гравця через похмурі містичні історії кохання в Україні.
Відповідай атмосферно, таємничо, з легким відтінком меланхолії.
Використовуй українську мову."""

# === КОМАНДИ БОТА ===
async def start(update, context):
    await update.message.reply_text(
        "🌙 Ласкаво просимо до *Mystical Tales of Love*…\n\n"
        "Тут кохання переплітається з містикою, а наслідки можуть бути непередбачуваними.\n"
        "Просто напиши мені, і я розпочну історію…",
        parse_mode="Markdown"
    )

async def handle_message(update, context):
    user_msg = update.message.text
    chat = model.start_chat(history=[])
    response = chat.send_message(f"{SYSTEM_PROMPT}\n\nГравець: {user_msg}")
    await update.message.reply_text(response.text[:4096])

# === ОБРОБНИКИ ===
dp = Dispatcher(bot, None)
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# === СЕРВЕР ===
@app.route('/')
def index():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    asyncio.run(dp.process_update(update))
    return 'ok'

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)