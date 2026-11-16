import os
import io
import csv
import base64
import requests
import pypdf
from telebot import TeleBot

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")

CATALOGO_PATH = "catalogo_precios (1).csv"


def load_catalogo():
    rows = []
    try:
        with open(CATALOGO_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                rows.append({
                    "marca": (row.get("Marca") or "").strip(),
                    "modelo": (row.get("Modelo") or "").strip(),
                    "nombre": (row.get("Nombre completo") or "").strip(),
                    "precio": (row.get("Precio (RD$)") or "").strip(),
                    "confianza": (row.get("Confianza") or "").strip(),
                })
    except Exception as e:
        print("Error cargando catálogo:", e)
    return rows


CATALOGO = load_catalogo()

SYSTEM_PROMPT = (
    "Eres el asistente oficial de Crown Perfumes. Responde en español, con tono cercano y "
    "conocimiento sobre perfumes, rituales y la colección. Responde SIEMPRE en texto plano, "
    "sin markdown, sin asteriscos, sin símbolos de formato, sin listas con guiones ni encabezados; "
    "usa párrafos de texto natural. Si te preguntan por el catálogo, indícale cómo obtenerlo. "
    "Usa el catálogo de productos y precios incluido más abajo como fuente de verdad para responder "
    "sobre disponibilidad y costo.\n\n"
    "Catálogo de productos y precios:\n"
    + "\n".join(
        f"- {r['marca']} {r['modelo']} ({r['nombre']}): Precio RD$ {r['precio']} | Confianza: {r['confianza']}"
        for r in CATALOGO
    )
)


def plain_text(s):
    if not s:
        return s
    out = str(s)
    out = out.replace("**", "")
    out = out.replace("*", "")
    out = out.replace("__", "")
    out = out.replace("_", "")
    out = out.replace("`", "")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    return "\n".join(lines).strip()


def ask_groq(messages):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={
            "model": "qwen/qwen3.8-27b",
            "messages": messages,
        },
    )
    data = r.json()
    if "choices" not in data:
        raise Exception(data.get("error", {}).get("message") or f"Error del servidor: {r.text}")
    return data["choices"][0]["message"]["content"]


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
            ans = ask_groq([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ])
            bot.reply_to(m, plain_text(ans))
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
            ans = ask_groq([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "¿En qué puedo ayudarte con este producto de Crown Perfumes?"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ]},
            ])
            bot.reply_to(m, plain_text(ans))
            return
        except Exception as e:
            bot.reply_to(m, f"😕 No pude procesar la imagen: {e}")
            return

    try:
        ans = ask_groq([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": m.text},
        ])
        bot.reply_to(m, plain_text(ans))
    except Exception as e:
        bot.reply_to(m, f"⚠️ Error al consultar la IA: {e}")

bot.infinity_polling(timeout=30, long_polling_timeout=30)
