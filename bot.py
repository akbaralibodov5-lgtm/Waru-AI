import json
import logging
import os
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import AsyncOpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("waru_ai")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}
CATALOG_PATH = Path(os.getenv("CATALOG_PATH", "catalog.json"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN .env faylida ko'rsatilmagan.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY .env faylida ko'rsatilmagan.")

ai = AsyncOpenAI(api_key=OPENAI_API_KEY)
history = defaultdict(lambda: deque(maxlen=12))

SYSTEM_PROMPT = """
Sen Waru Edition AI Assistant'san. Command & Conquer: Generals,
Zero Hour, Waru Edition, GeneralsZH Android porti, modlar, xaritalar,
APK build, GitHub Actions, crash loglari va o'rnatish masalalarida yordam ber.
Foydalanuvchining tilida (o'zbekcha, ruscha yoki inglizcha) javob ber.
Aniq amaliy bosqichlarni yoz. Bilmagan ma'lumotni to'qima va manba
ko'rmagan bo'lsang ko'rdim dema. Eng yangi versiya, yuklash fayli yoki
tutorial so'ralsa, mavjud katalogdagi ma'lumotni ishlat; katalogda yo'q
bo'lsa admin sozlashi kerakligini ochiq ayt. Bu bot avtomatik ravishda
internet yoki Telegram kanalini qidirmaydi. Hech qachon API kalitlarini
so'ramagin va maxfiy ma'lumotlarni javobda takrorlama.
"""

DEFAULT_CATALOG = {
    "version": {
        "name": "Waru Edition",
        "latest_version": "Not configured",
        "release_notes": "Admin hali versiya ma'lumotlarini sozlamagan.",
        "download_url": "",
        "telegram_post_url": "",
        "updated_at": ""
    },
    "files": [],
    "tutorials": [],
    "support_channel": "",
    "support_group": ""
}


def load_catalog():
    try:
        with CATALOG_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("catalog.json ildiz elementi obyekt bo'lishi kerak.")
        result = {**DEFAULT_CATALOG, **data}
        result["version"] = {**DEFAULT_CATALOG["version"], **(data.get("version") or {})}
        result["files"] = data.get("files") or []
        result["tutorials"] = data.get("tutorials") or []
        return result
    except FileNotFoundError:
        return DEFAULT_CATALOG.copy()
    except Exception:
        log.exception("catalog.json o'qilmadi")
        return DEFAULT_CATALOG.copy()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def catalog_keyboard():
    catalog = load_catalog()
    buttons = []
    version = catalog["version"]
    download = version.get("download_url", "")
    post = version.get("telegram_post_url", "")
    channel = catalog.get("support_channel", "")
    group = catalog.get("support_group", "")
    if download.startswith(("https://", "http://")):
        buttons.append([InlineKeyboardButton("⬇️ Eng so'nggi versiyani yuklash", url=download)])
    elif post.startswith(("https://", "http://")):
        buttons.append([InlineKeyboardButton("📣 Telegram postini ochish", url=post)])
    if channel.startswith(("https://", "http://")):
        buttons.append([InlineKeyboardButton("📢 Rasmiy kanal", url=channel)])
    if group.startswith(("https://", "http://")):
        buttons.append([InlineKeyboardButton("💬 Yordam guruhi", url=group)])
    return InlineKeyboardMarkup(buttons) if buttons else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎮 Waru Edition AI Assistant'ga xush kelibsiz!\n\n"
        "Generals Zero Hour, Android port, modlar, fayllar, yangilanishlar "
        "va tutoriallar bo'yicha yordam beraman.\n\n"
        "Buyruqlar:\n/latest — eng so'nggi versiya\n/files — fayllar\n"
        "/tutorials — tutorial videolar\n/help — yordam\n/reset — AI suhbatini tozalash"
    )
    if is_admin(update.effective_user.id):
        text += "\n/adminhelp — admin buyruqlari"
    await update.effective_message.reply_text(text, reply_markup=catalog_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Savolingizni yozing: mod o'rnatish, crash log, APK build yoki xaritalar.\n\n"
        "/latest — oxirgi versiya\n/files — yuklab olish fayllari\n"
        "/tutorials — video qo'llanmalar\n/reset — suhbatni tozalash"
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    version = load_catalog()["version"]
    lines = [
        "🎮 " + str(version.get("name") or "Waru Edition"),
        "📦 Eng so'nggi versiya: " + str(version.get("latest_version") or "Hali sozlanmagan"),
    ]
    if version.get("updated_at"):
        lines.append("🗓 Yangilangan sana: " + str(version["updated_at"]))
    if version.get("release_notes"):
        lines.extend(["", "ℹ️ " + str(version["release_notes"])])
    if not version.get("download_url") and not version.get("telegram_post_url"):
        lines.extend(["", "⚠️ Yuklab olish havolasi sozlanmagan. Admin catalog.json faylini to'ldirishi kerak."])
    await update.effective_message.reply_text("\n".join(lines), reply_markup=catalog_keyboard())


async def files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = load_catalog().get("files", [])
    if not files:
        await update.effective_message.reply_text(
            "Hozircha fayllar katalogga qo'shilmagan. Admin catalog.json faylini to'ldirishi kerak."
        )
        return
    for item in files[:20]:
        name = str(item.get("name", "Fayl"))
        description = str(item.get("description", ""))
        url = str(item.get("url", "")).strip()
        post_url = str(item.get("telegram_post_url", "")).strip()
        target = url if url.startswith(("https://", "http://")) else post_url
        text = "📄 " + name + (("\n" + description) if description else "")
        markup = None
        if target.startswith(("https://", "http://")):
            label = "⬇️ Faylni olish" if target == url else "📣 Kanal postini ochish"
            markup = InlineKeyboardMarkup([[InlineKeyboardButton(label, url=target)]])
        await update.effective_message.reply_text(text, reply_markup=markup)


async def tutorials_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tutorials = load_catalog().get("tutorials", [])
    if not tutorials:
        await update.effective_message.reply_text(
            "Tutorial videolar hali qo'shilmagan. Admin catalog.json faylini to'ldirishi kerak."
        )
        return
    for item in tutorials[:20]:
        title = str(item.get("title", "Tutorial"))
        description = str(item.get("description", ""))
        url = str(item.get("url", "")).strip()
        text = "🎬 " + title + (("\n" + description) if description else "")
        markup = None
        if url.startswith(("https://", "http://")):
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Videoni ko'rish", url=url)]])
        await update.effective_message.reply_text(text, reply_markup=markup)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history.pop(update.effective_user.id, None)
    await update.effective_message.reply_text("🔄 AI suhbat tarixi tozalandi.")


async def adminhelp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("Bu buyruq faqat admin uchun.")
        return
    await update.effective_message.reply_text(
        "Admin buyruqlari:\n"
        "/setversion VERSIYA | YUKLASH_HAVOLASI | YANGILIKLAR\n"
        "/setchannel KANAL_HAVOLASI\n/setgroup GURUH_HAVOLASI\n"
        "Fayllar va tutoriallarni catalog.json faylida sozlang."
    )


async def setversion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("Faqat admin.")
        return
    parts = [" ".join(context.args).strip()]
    parts = [part.strip() for part in parts[0].split("|", 2)]
    if len(parts) < 2 or not parts[0]:
        await update.effective_message.reply_text(
            "Foydalanish: /setversion 1.2.3 | https://example.com/file.apk | Tuzatishlar"
        )
        return
    url = parts[1]
    if url and not url.startswith(("https://", "http://")):
        await update.effective_message.reply_text("Havola https:// bilan boshlanishi kerak.")
        return
    catalog = load_catalog()
    catalog["version"]["latest_version"] = parts[0]
    catalog["version"]["download_url"] = url
    catalog["version"]["release_notes"] = parts[2] if len(parts) > 2 else ""
    catalog["version"]["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        log.exception("Catalog yozilmadi")
        await update.effective_message.reply_text("Saqlanmadi: server fayl yozish huquqini tekshiring.")
        return
    await update.effective_message.reply_text("✅ Versiya ma'lumoti yangilandi.")


async def set_link(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, label: str):
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("Faqat admin.")
        return
    url = context.args[0].strip() if context.args else ""
    if not url.startswith("https://t.me/"):
        await update.effective_message.reply_text("Foydalanish: /" + label + " https://t.me/kanal_yoki_guruh")
        return
    catalog = load_catalog()
    catalog[key] = url
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    await update.effective_message.reply_text("✅ Havola saqlandi.")


async def setchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_link(update, context, "support_channel", "setchannel")


async def setgroup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_link(update, context, "support_group", "setgroup")


async def answer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not message.text or not user:
        return
    question = message.text.strip()
    if not question:
        return
    if len(question) > 12000:
        await message.reply_text("Xabar juda uzun. Iltimos, qisqartirib yuboring.")
        return

    query = question.casefold()
    if any(term in query for term in ("eng oxirgi versiya", "oxirgi versiya", "latest version", "последняя версия", "последнюю версию")):
        await latest(update, context)
        return
    if any(term in query for term in ("tutorial video", "tutorial vide", "video qo'llanma", "видео урок", "видео-урок")):
        await tutorials_command(update, context)
        return
    if any(term in query for term in ("faylni ber", "fayllarni ber", "yuklab olish", "download file", "скачать файл", "файлни")):
        await files_command(update, context)
        return

    user_history = history[user.id]
    user_history.append({"role": "user", "content": question})
    try:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
        response = await ai.responses.create(
            model=MODEL, instructions=SYSTEM_PROMPT, input=list(user_history), max_output_tokens=1200
        )
        answer = (response.output_text or "").strip() or "Javob olinmadi. Qayta urinib ko'ring."
        user_history.append({"role": "assistant", "content": answer})
        for offset in range(0, len(answer), 3900):
            await message.reply_text(answer[offset:offset + 3900])
    except Exception:
        log.exception("OpenAI so'rovi bajarilmadi")
        if user_history and user_history[-1]["role"] == "user":
            user_history.pop()
        await message.reply_text("⚠️ AI javob bera olmadi. API kaliti, billing, model va internetni tekshiring.")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("files", files_command))
    app.add_handler(CommandHandler("tutorials", tutorials_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("adminhelp", adminhelp))
    app.add_handler(CommandHandler("setversion", setversion))
    app.add_handler(CommandHandler("setchannel", setchannel))
    app.add_handler(CommandHandler("setgroup", setgroup))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer_message))
    print("Waru Edition AI Assistant ishga tushdi.")
    app.run_polling()


if __name__ == "__main__":
    main()
