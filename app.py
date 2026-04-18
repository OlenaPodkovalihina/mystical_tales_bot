import os
from flask import Flask, request
from telegram import Bot, Update
import google.generativeai as genai

TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

bot = Bot(token=TOKEN)
app = Flask(__name__)

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = "Ти — оповідач. Відповідай українською."

@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    if update and update.message:
        user_msg = update.message.text
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\nГравець: {user_msg}")
        bot.send_message(chat_id=update.message.chat_id, text=response.text)
    return 'ok'

@app.route('/')
def index():
    return "Bot is running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)