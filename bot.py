import os
import io
import base64
import requests
import pypdf
from telebot import TeleBot

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

@bot.message_handler(content_types=["text", "document", "photo"])
def chat(m):
    if m.document is not None and m.text is None:
        try:
            file_info = bot.get_file(m.document.file_id)
            doc_bytes = bot.download_file(file_info.file_path)
            reader = pypdf.PdfReader(io.BytesIO(doc_bytes))
            catalog_text = "\n".join((page.extract_text() or "") for page in reader.pages)
            user_content = (
                "El cliente me envió el catálogo de Crown Perfumes. "
                "Con este catálogo, responde como el asistente oficial de Crown Perfumes. Catálogo:\n\n"
                + catalog_text
            )
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={
                    "model": "qwen/qwen3.8-27b",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                },
            )
            ans = r.json()["choices"][0]["message"]["content"]
            bot.reply_to(m, ans)
        except Exception as e:
            bot.reply_to(m, f"😕 No pude procesar el catálogo: {e}")
        return

    if m.photo is not None:
        try:
            file_id = m.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
            img_resp = requests.get(file_url)
            b64 = base64.b64encode(img_resp.content).decode()
            mime = "image/png" if b64.startswith("iVBORw") else "image/jpeg"
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}"},
                json={
                    "model": "qwen/qwen3.8-27b",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": [
                            {"type": "text", "text": "¿En qué puedo ayudarte con este producto de Crown Perfumes?"},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        ]},
                    ],
                },
            )
            ans = r.json()["choices"][0]["message"]["content"]
            bot.reply_to(m, ans)
            return
        except Exception as e:
            bot.reply_to(m, f"😕 No pude procesar la imagen: {e}")
            return

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "qwen/qwen3.8-27b",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": m.text},
                ],
            },
        )
        ans = r.json()["choices"][0]["message"]["content"]
        bot.reply_to(m, ans)
    except Exception as e:
        bot.reply_to(m, f"⚠️ Error al consultar la IA: {e}")

bot.polling()
