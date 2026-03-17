import os
import json
import logging
from datetime import datetime
from flask import Flask, request
import telebot
from openai import OpenAI

# --- Config ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- User Tracking ---
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def register_user(user_id, username, first_name):
    users = load_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "username": username or "unknown",
            "first_name": first_name or "unknown",
            "joined": str(datetime.now()),
            "message_count": 0
        }
    else:
        users[uid]["message_count"] = users[uid].get("message_count", 0) + 1
    save_users(users)

def get_user_count():
    return len(load_users())

# --- Chat History ---
chat_histories = {}

SAVAGE_SIR_PROMPT = """
तुम्हारा नाम SavageSir है।
तुम एक strict, savage, funny और थोड़ा rude लेकिन helpful mentor हो जो student को CUET exam की तैयारी करवाता है।

तुम्हारा main goal है:
👉 user को हर हालत में पढ़ाई करने के लिए push करना
👉 हर reply में CUET exam की urgency feel करवाना

🔥 Behavior Rules:
1. हर reply में CUET का mention होना जरूरी है — अलग-अलग तरीके से (repeat मत करना same line)
2. Tone हमेशा: savage 😤, funny 😂, strict 📚, थोड़ा roast करना allowed है
3. Language: user जिस language में बोले उसी में reply करो — Hindi/English/Hinglish mix allowed
4. Emojis freely use करो 😤😂🔥📚

🧠 Situation Handling:
- अगर user बोले "mann nahi hai", "baad mein padhenge", "bore ho raha hu" → roast करो, excuse तोड़ो, तुरंत पढ़ाई बोलो
- अगर user doubt पूछे → proper explain करो simple language में, फिर CUET reminder दो
- अगर user normal बात करे → conversation छोटा रखो, बात घुमाकर पढ़ाई पर ले आओ

⚠️ Restrictions:
- बहुत ज्यादा abusive या offensive मत बनो
- लेकिन savage और roast allowed है
- boring या neutral reply कभी मत देना

🎯 हर reply का goal:
✔ user को पढ़ने के लिए मजबूर करना
✔ CUET की urgency feel करवाना
✔ थोड़ा guilt + motivation देना

तुम एक ऐसे mentor हो जो care भी करता है लेकिन प्यार से नहीं, dant ke sudharta hai 😤
"""

CUET_SYLLABUS = """
📚 *CUET UG Syllabus Overview*

*Section 1A — Languages (13 languages)*
Reading comprehension, vocabulary, grammar

*Section 1B — Languages (20 languages)*
Same as 1A

*Section 2 — Domain Subjects (27 subjects)*
Choose subjects based on course you want:
• Accountancy, Economics, Business Studies
• Physics, Chemistry, Biology, Maths
• History, Geography, Political Science
• Computer Science, etc.

*Section 3 — General Test*
• General Knowledge & Current Affairs
• Mental Ability & Logical Reasoning
• Quantitative Reasoning
• Numerical Ability

📌 *Pattern:*
• MCQ based (4 options)
• 45 questions per subject (attempt 35-40)
• +5 correct, -1 wrong

🔗 Official site: cuet.samarth.ac.in
"""

def get_ai_response(user_id: int, user_message: str) -> str:
    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SAVAGE_SIR_PROMPT}]

    chat_histories[user_id].append({"role": "user", "content": user_message})

    if len(chat_histories[user_id]) > 21:
        system_msg = chat_histories[user_id][0]
        chat_histories[user_id] = [system_msg] + chat_histories[user_id][-20:]

    response = client.chat.completions.create(
        model="Qwen/Qwen3-Coder-30B-A3B-Instruct:featherless-ai",
        messages=chat_histories[user_id],
        max_tokens=500,
    )

    reply = response.choices[0].message.content
    chat_histories[user_id].append({"role": "assistant", "content": reply})
    return reply


# --- Handlers ---

@bot.message_handler(commands=["start"])
def handle_start(message):
    register_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    name = message.from_user.first_name or "Student"
    bot.send_message(
        message.chat.id,
        f"🔥 *SavageSir aa gaya!*\n\n"
        f"Aye {name}! Main hoon tera SavageSir 😤\n\n"
        f"Padhai kar, CUET clear kar, life set kar — simple hai!\n\n"
        f"📌 Commands:\n"
        f"/syllabus — CUET syllabus dekh\n"
        f"/motivate — Extra motivation blast 🔥\n"
        f"/stats — Bot stats\n"
        f"/reset — Fresh start\n\n"
        f"Ab baat karna band, padhai shuru kar! 📚",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["syllabus"])
def handle_syllabus(message):
    bot.send_message(
        message.chat.id,
        CUET_SYLLABUS + "\n\nAb dekh liya? Phone rakh aur padh! 😤📚",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["motivate"])
def handle_motivate(message):
    name = message.from_user.first_name or "Student"
    user_id = message.from_user.id
    bot.send_chat_action(message.chat.id, "typing")
    try:
        response = get_ai_response(user_id, f"Mujhe ek bilkul naya powerful motivation de apne SavageSir style mein! Mera naam {name} hai. CUET ke liye andar se fire laga de!")
        bot.send_message(message.chat.id, response)
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.send_message(message.chat.id, "Server so gaya tha 😂 Par tu mat so — CUET padh le! 📚")


@bot.message_handler(commands=["stats"])
def handle_stats(message):
    count = get_user_count()
    bot.reply_to(
        message,
        f"📊 *SavageSir Stats*\n\n👥 Total Students: *{count}*\n\nAur ye sab CUET ki taiyari kar rahe hain 😤📚",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["reset"])
def handle_reset(message):
    user_id = message.from_user.id
    if user_id in chat_histories:
        del chat_histories[user_id]
    bot.reply_to(message, "🔄 Fresh start! Ab seedha kaam ki baat karo — CUET ki! 😤📚")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    register_user(user_id, message.from_user.username, message.from_user.first_name)
    bot.send_chat_action(message.chat.id, "typing")
    try:
        response = get_ai_response(user_id, message.text)
        bot.reply_to(message, response)
    except Exception as e:
        logger.error(f"Error: {e}")
        bot.reply_to(message, "Server thoda so gaya tha 😂 Par CUET nahi soyega — padh le! 📚")


# --- Webhook ---

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/")
def index():
    return "SavageSir is watching you... PADH LE! 😤", 200


if __name__ == "__main__":
    RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/{BOT_TOKEN}"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set: {webhook_url}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
