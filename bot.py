import os
from telebot import TeleBot
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

SYSTEM_PROMPT = (
    "Eres el asistente oficial de Crown Perfumes. Responde en español, con tono cercano y "
    "conocimiento sobre perfumes, rituales y la colección. Si te preguntan por el catálogo, "
    "indica cómo obtenerlo."
)

bot = TeleBot(TOKEN)

@bot.message_handler(commands=["start"])
def start(m):
    bot.reply_to(m, "👑 ¡Hola! Soy el asistente de Crown Perfumes. Puedo ayudarte con perfumes, rituales y la colección.")

@bot.message_handler(content_types=["text", "document"])
def chat(m):
    if m.text is None and m.document is not None:
        bot.reply_to(m, "📄 Recibí el catálogo. Déjame revisarlo y te ayudo con tu consulta.")
        return

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": m.text},
            ],
        },
    )
    ans = r.json()["choices"][0]["message"]["content"]
    bot.reply_to(m, ans)

bot.polling()
