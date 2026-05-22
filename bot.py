"""
Norbekov Markazi - Telegram Support Bot
OpenRouter (DeepSeek) bilan ishlaydi
"""

import os
import logging

# socks5h proxy'ni o'chirish (httpx uni qo'llab-quvvatlamaydi)
for _var in ("ALL_PROXY", "all_proxy", "GRPC_PROXY", "grpc_proxy",
             "FTP_PROXY", "ftp_proxy", "RSYNC_PROXY"):
    os.environ.pop(_var, None)

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import httpx

from knowledge_base import SYSTEM_PROMPT

# .env fayldan tokenlarni yuklash
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")

# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Foydalanuvchilarning suhbat tarixi (xotira)
conversation_history: dict[int, list] = {}
MAX_HISTORY = 10  # Har bir foydalanuvchi uchun maksimal xabar soni


async def ask_deepseek(user_id: int, user_message: str) -> str:
    """OpenRouter orqali DeepSeek modeliga savol yuboradi."""

    # Foydalanuvchi tarixini olish yoki yangi boshlash
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]

    # Yangi xabarni tarixga qo'shish
    history.append({"role": "user", "content": user_message})

    # Tarix uzunligini cheklash
    if len(history) > MAX_HISTORY * 2:
        history = history[-MAX_HISTORY * 2:]
        conversation_history[user_id] = history

    # OpenRouter API so'rovi
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://norbekov-support-bot.com",
                "X-Title": "Norbekov Support Bot",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1024,
            },
        )
        response.raise_for_status()
        data = response.json()

    assistant_message = data["choices"][0]["message"]["content"]

    # Bot javobini tarixga qo'shish
    history.append({"role": "assistant", "content": assistant_message})

    return assistant_message


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start buyrug'i"""
    user_name = update.effective_user.first_name or "Hurmatli foydalanuvchi"

    # Foydalanuvchi tarixini tozalash
    if update.effective_user.id in conversation_history:
        conversation_history.pop(update.effective_user.id)

    welcome_text = (
        f"Assalomu alaykum, {user_name}! 👋\n\n"
        "Men Mirzakarim Norbekov markazi rasmiy support botiman.\n\n"
        "Markaz haqida quyidagi mavzularda yordam bera olaman:\n"
        "• Kurslar va o'quv dasturlari\n"
        "• Norbekov tizimi va metodologiyasi\n"
        "• Markaz faoliyati va xizmatlari\n\n"
        "Savolingizni yozing, men javob berishga tayyorman! 🌟"
    )
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help buyrug'i"""
    help_text = (
        "📋 *Bot buyruqlari:*\n\n"
        "/start — Botni qayta boshlash\n"
        "/help — Yordam\n"
        "/about — Markaz haqida qisqacha\n"
        "/clear — Suhbat tarixini tozalash\n\n"
        "Har qanday savolingizni shunchaki yozing — men javob beraman!"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/about buyrug'i"""
    about_text = (
        "🏛 *Mirzakarim Norbekov Markazi*\n\n"
        "O'quv-sog'lomlashtirish markazi — insonning ichki imkoniyatlarini "
        "ochish, salomatlikni tiklash va shaxsiy samaradorlikni oshirishga "
        "qaratilgan mualliflik metodologiyasi asosida ishlaydigan muassasa.\n\n"
        "Asoschi: Professor Mirzakarim Sanakulovich Norbekov\n\n"
        "Kurslar haqida batafsil ma'lumot olish uchun savolingizni yozing!"
    )
    await update.message.reply_text(about_text, parse_mode="Markdown")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/clear buyrug'i — suhbat tarixini tozalash"""
    if update.effective_user.id in conversation_history:
        conversation_history.pop(update.effective_user.id)
    await update.message.reply_text("✅ Suhbat tarixi tozalandi. Yangi savol berishingiz mumkin!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Oddiy xabarlarni qayta ishlash"""
    user_id = update.effective_user.id
    user_message = update.message.text

    # Yozmoqda... ko'rsatish
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        response = await ask_deepseek(user_id, user_message)
        await update.message.reply_text(response)

    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter API xatosi: {e}")
        await update.message.reply_text(
            "Kechirasiz, hozir texnik muammo yuzaga keldi. "
            "Bir oz kutib qayta urinib ko'ring. 🙏"
        )
    except Exception as e:
        logger.error(f"Kutilmagan xato: {e}")
        await update.message.reply_text(
            "Xatolik yuz berdi. Iltimos, /start buyrug'i bilan qayta boshlang."
        )


def main() -> None:
    """Botni ishga tushirish"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN o'rnatilmagan! .env faylini tekshiring.")
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY o'rnatilmagan! .env faylini tekshiring.")

    logger.info("Norbekov Support Bot ishga tushmoqda...")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Buyruq handlerlari
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("clear", clear_command))

    # Matn xabarlari handleri
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot tayyor! Telegram xabarlarini kutmoqda...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
