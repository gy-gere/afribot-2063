"""
bot/telegram_bot.py — AfriBot-2063 Telegram Bot Interface

Features:
  - Amharic + English chat with AfriBot
  - Voice message support (via Whisper STT)
  - /start, /help, /status, /ingest commands
  - Inline topic buttons

Setup:
  1. Create a bot via @BotFather on Telegram → get token
  2. export TELEGRAM_BOT_TOKEN="your_token"
  3. python bot/telegram_bot.py

Run:  python bot/telegram_bot.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import tempfile

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from utils.logger   import get_logger
from utils.internet import is_online

log = get_logger("telegram_bot")

# ── Config ────────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# Per-user state: tracks language preference
user_state: dict[int, dict] = {}


def get_user(user_id: int) -> dict:
    if user_id not in user_state:
        user_state[user_id] = {"lang": "auto", "force_offline": False, "count": 0}
    return user_state[user_id]


# ── Keyboards ─────────────────────────────────────────────────────────────────

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Faraday's Law", callback_data="q:What is Faraday's Law?"),
            InlineKeyboardButton("🧲 Magnetic Circuits", callback_data="q:What is magnetomotive force?"),
        ],
        [
            InlineKeyboardButton("🔄 Transformers", callback_data="q:How does a transformer work?"),
            InlineKeyboardButton("⚙️ DC Motors", callback_data="q:How does a DC motor work?"),
        ],
        [
            InlineKeyboardButton("🇪🇹 ፋራዳይ ህግ", callback_data="q:ፋራዳይ ህግ ምንድን ነው?"),
            InlineKeyboardButton("📊 Status", callback_data="status"),
        ],
        [
            InlineKeyboardButton("🌐 Toggle Offline", callback_data="toggle_offline"),
        ],
    ])


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = get_user(user.id)
    mode = "🟢 Online (Gemini)" if is_online() else "🔴 Offline (Ollama)"

    await update.message.reply_text(
        f"👋 Hello {user.first_name}! I'm *AfriBot-2063*.\n\n"
        f"I can teach you about *electrical machines, electronics, robotics,* and *TVET* content "
        f"from Debre Berhan University.\n\n"
        f"I speak *English* 🇬🇧 and *Amharic* 🇪🇹 — just ask in either language!\n\n"
        f"Current mode: {mode}\n\n"
        f"Tap a topic below or just type your question:",
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*AfriBot-2063 Commands:*\n\n"
        "/start — Welcome message & topic menu\n"
        "/help  — This help message\n"
        "/status — System status & stats\n"
        "/offline — Toggle offline mode\n"
        "/ingest — Re-index PDF knowledge base\n"
        "/clear — Reset your conversation\n\n"
        "*Tips:*\n"
        "• Ask questions in English or Amharic\n"
        "• Send a *voice message* 🎤 and I'll transcribe it\n"
        "• I use your textbook as context for every answer",
        parse_mode="Markdown",
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state = get_user(update.effective_user.id)
    online = is_online()

    try:
        from rag.query import get_collection
        chunks = get_collection().count()
    except Exception:
        chunks = 0

    from models.local_llm import is_ollama_running
    ollama_ok = is_ollama_running()

    lines = [
        "📊 *AfriBot-2063 Status*\n",
        f"🌐 Internet:  {'✅ Connected' if online else '❌ Offline'}",
        f"☁️ Gemini:    {'✅ Available' if online else '❌ Unavailable'}",
        f"🖥️ Ollama:    {'✅ Running' if ollama_ok else '⚠️ Not running'}",
        f"🧠 DB Chunks: {chunks}",
        f"\n👤 Your session:",
        f"   Queries answered: {state['count']}",
        f"   Force offline: {'ON' if state['force_offline'] else 'OFF'}",
    ]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_offline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state = get_user(update.effective_user.id)
    state["force_offline"] = not state["force_offline"]
    status = "ON 🖥️" if state["force_offline"] else "OFF ☁️"
    await update.message.reply_text(
        f"Offline mode: *{status}*\n"
        f"{'Now using local Ollama only.' if state['force_offline'] else 'Will use Gemini when available.'}",
        parse_mode="Markdown",
    )


async def cmd_ingest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📥 Ingesting PDF knowledge base… this may take a few minutes.")
    try:
        from rag.ingest import ingest_all
        n = ingest_all(force=False)
        await update.message.reply_text(f"✅ Done! {n} new chunks added to the knowledge base.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ingest failed: {e}")


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in user_state:
        count = user_state[uid].get("count", 0)
        user_state[uid] = {"lang": "auto", "force_offline": False, "count": 0}
    await update.message.reply_text("🗑️ Session cleared. Start fresh!")


# ── Message handler ───────────────────────────────────────────────────────────

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    question = update.message.text.strip()
    if not question:
        return

    state = get_user(update.effective_user.id)
    state["count"] += 1

    await ctx.bot.send_chat_action(update.effective_chat.id, "typing")

    try:
        from language.detect import detect_language
        from models.router   import answer

        lang = detect_language(question)
        resp, source = answer(
            question,
            language=lang,
            force_offline=state["force_offline"],
        )

        source_label = {
            "gemini":   "☁️ Gemini",
            "local":    "🖥️ Ollama",
            "fallback": "⚠️ Fallback",
        }.get(source, source)

        lang_flag = "🇪🇹" if lang == "am" else "🇬🇧"

        await update.message.reply_text(
            f"{resp}\n\n_{source_label} · {lang_flag}_",
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception as e:
        log.error(f"Error handling message: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Something went wrong. Please try again or check /status"
        )


# ── Voice message handler ─────────────────────────────────────────────────────

async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Transcribe voice message and answer it."""
    await update.message.reply_text("🎤 Transcribing your voice message…")
    await ctx.bot.send_chat_action(update.effective_chat.id, "typing")

    try:
        voice = update.message.voice
        file  = await ctx.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)

        # Convert ogg → wav for Whisper
        wav_path = tmp_path.replace(".ogg", ".wav")
        os.system(f"ffmpeg -y -i {tmp_path} -ar 16000 -ac 1 {wav_path} -loglevel quiet")

        from speech.stt import transcribe_file
        transcript = transcribe_file(wav_path)

        os.unlink(tmp_path)
        if os.path.exists(wav_path):
            os.unlink(wav_path)

        if not transcript:
            await update.message.reply_text("⚠️ Could not transcribe audio. Please try again or type your question.")
            return

        await update.message.reply_text(f"🗣️ *Heard:* {transcript}", parse_mode="Markdown")

        # Now answer as if it were a text message
        update.message.text = transcript
        await handle_text(update, ctx)

    except Exception as e:
        log.error(f"Voice error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Voice processing failed: {e}")


# ── Callback query handler ────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "status":
        await cmd_status(update, ctx)

    elif data == "toggle_offline":
        state = get_user(update.effective_user.id)
        state["force_offline"] = not state["force_offline"]
        label = "ON 🖥️" if state["force_offline"] else "OFF ☁️"
        await query.edit_message_reply_markup(reply_markup=main_keyboard())
        await ctx.bot.send_message(
            update.effective_chat.id,
            f"Offline mode: *{label}*",
            parse_mode="Markdown",
        )

    elif data.startswith("q:"):
        question = data[2:]
        update.callback_query.message.text = question
        # Simulate text message
        class FakeMsg:
            text = question
            def __getattr__(self, n):
                return getattr(query.message, n)
        update._message = FakeMsg()
        await handle_text(update, ctx)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    if TELEGRAM_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("❌ Set TELEGRAM_BOT_TOKEN environment variable first.")
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        sys.exit(1)

    # Auto-ingest PDFs if DB empty
    try:
        from rag.query  import get_collection
        from rag.ingest import ingest_all
        if get_collection().count() == 0:
            print("📥 Auto-ingesting PDFs…")
            ingest_all()
    except Exception as e:
        print(f"⚠️ Could not auto-ingest: {e}")

    print("🤖 AfriBot-2063 Telegram Bot starting…")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("offline", cmd_offline))
    app.add_handler(CommandHandler("ingest",  cmd_ingest))
    app.add_handler(CommandHandler("clear",   cmd_clear))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
