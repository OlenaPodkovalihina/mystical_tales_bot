import os
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import google.generativeai as genai

# === НАЛАШТУВАННЯ ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not TOKEN or not GEMINI_KEY:
    raise ValueError("Missing TELEGRAM_TOKEN or GEMINI_API_KEY")

# Flask для healthcheck (щоб Render не вбивав бота)
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

@app.route('/health')
def health():
    return "OK"

# Ініціалізація Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# === ТВІЙ ПЕРСОНАЖ (тимчасовий, потім заміниш на повний) ===
SYSTEM_PROMPT = """Ти — оповідач у грі "Mystical Tales of Love: Delissimo".
Гравець щойно приїхав до готелю. Опиши, що вона бачить: старий особняк, ліс навколо, тишу.
Відповідай атмосферно, таємничо, з легким відтінком меланхолії.
Використовуй українську мову."""

# === ОБРОБНИКИ КОМАНД ===
async def start(update: Update, context):
    await update.message.reply_text(
        "🌙 Ласкаво просимо до *Mystical Tales of Love*…\n\n"
        "Тут кохання переплітається з містикою, а наслідки можуть бути непередбачуваними.\n"
        "Просто напиши мені, і я розпочну історію…",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context):
    user_msg = update.message.text
    chat = model.start_chat(history=[])
    response = chat.send_message(f"{SYSTEM_PROMPT}\n\nГравець: {user_msg}")
    await update.message.reply_text(response.text[:4096])

# === ЗАПУСК БОТА ===
def main():
    # Створюємо бота
    application = Application.builder().token(TOKEN).build()
    
    # Додаємо обробники
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаємо бота в режимі polling (простіше, ніж webhook)
    print("Бот запущено в режимі polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    # Запускаємо Flask у фоновому потоці для healthcheck
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))).start()
    
    # Запускаємо бота
    main()