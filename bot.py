import os
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------- Logging ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------- Token from Railway env variable ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN environment variable is not set!")

# ---------- Simple synonym dictionary (self-contained, no external API) ----------
SYNONYMS = {
    "good": ["great", "excellent", "fine", "positive", "decent"],
    "bad": ["poor", "awful", "negative", "unpleasant", "subpar"],
    "happy": ["glad", "joyful", "pleased", "cheerful", "content"],
    "sad": ["unhappy", "sorrowful", "down", "gloomy", "melancholy"],
    "big": ["large", "huge", "massive", "enormous", "substantial"],
    "small": ["tiny", "little", "minor", "compact", "slight"],
    "fast": ["quick", "rapid", "swift", "speedy", "brisk"],
    "slow": ["sluggish", "leisurely", "unhurried", "gradual"],
    "important": ["crucial", "vital", "significant", "essential", "key"],
    "difficult": ["hard", "challenging", "tough", "complex", "demanding"],
    "easy": ["simple", "effortless", "straightforward", "uncomplicated"],
    "smart": ["clever", "intelligent", "bright", "wise", "sharp"],
    "beautiful": ["pretty", "gorgeous", "lovely", "attractive", "stunning"],
    "angry": ["furious", "irritated", "annoyed", "mad", "upset"],
    "interesting": ["fascinating", "intriguing", "engaging", "captivating"],
}

# ---------- Rewrite templates (rule-based, no external service) ----------
def rewrite_text(text: str, tone: str) -> str:
    """
    Simple rule-based rewrite. Doesn't call any external API.
    """
    text = text.strip()
    if not text:
        return "Please send some text to rewrite."

    # Replace common words with synonyms based on tone
    replacements = {
        "formal": {
            "don't": "do not",
            "can't": "cannot",
            "won't": "will not",
            "it's": "it is",
            "i'm": "I am",
            "gonna": "going to",
            "wanna": "want to",
            "a lot of": "a great deal of",
            "get": "obtain",
            "ok": "acceptable",
        },
        "casual": {
            "do not": "don't",
            "cannot": "can't",
            "will not": "won't",
            "it is": "it's",
            "I am": "I'm",
            "going to": "gonna",
            "want to": "wanna",
            "obtain": "get",
            "acceptable": "ok",
        },
        "confident": {
            "I think": "I'm certain",
            "maybe": "definitely",
            "perhaps": "certainly",
            "I guess": "I know",
            "might": "will",
            "could be": "is",
            "sort of": "",
            "kind of": "",
        },
    }

    result = text
    if tone in replacements:
        for src, dst in replacements[tone].items():
            result = re.sub(re.escape(src), dst, result, flags=re.IGNORECASE)

    # Capitalize first letter
    if result:
        result = result[0].upper() + result[1:]

    return result


def get_synonyms(word: str):
    word = word.lower().strip()
    return SYNONYMS.get(word, [])


def count_text(text: str):
    words = len(re.findall(r"\b\w+\b", text))
    chars = len(text)
    chars_no_space = len(text.replace(" ", ""))
    sentences = len(re.findall(r"[.!?]+", text)) or (1 if text.strip() else 0)
    return words, chars, chars_no_space, sentences


def format_text(text: str, mode: str) -> str:
    if mode == "upper":
        return text.upper()
    if mode == "lower":
        return text.lower()
    if mode == "title":
        return text.title()
    if mode == "sentence":
        return ". ".join(s.strip().capitalize() for s in re.split(r"[.!?]+", text) if s.strip()) + "."
    if mode == "reverse":
        return text[::-1]
    return text


# ---------- Command handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "friend"
    text = (
        f"👋 Hi {user}!\n\n"
        "I'm *Wordtune*, your writing assistant.\n\n"
        "Here's what I can do:\n"
        "• /rewrite – Rewrite your text in a tone\n"
        "• /synonyms – Find synonyms for a word\n"
        "• /count – Count words, characters, sentences\n"
        "• /format – Change text case/formatting\n"
        "• /help – Show all commands\n"
        "• /about – About this bot\n\n"
        "Or just *send me any text* and I'll suggest actions."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Available Commands*\n\n"
        "/start – Welcome message\n"
        "/help – This help text\n"
        "/rewrite <text> – Rewrite in formal/casual/confident tone\n"
        "/synonyms <word> – Get synonym suggestions\n"
        "/count <text> – Count words, chars, sentences\n"
        "/format <text> – Format text (upper/lower/title/sentence)\n"
        "/about – About Wordtune Bot\n\n"
        "*Examples:*\n"
        "`/rewrite I can't go to the party`\n"
        "`/synonyms happy`\n"
        "`/count Hello world. How are you?`\n"
        "`/format hello world`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def about_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*About Wordtune Bot*\n\n"
        "A free writing assistant that helps you:\n"
        "• Rewrite sentences in different tones\n"
        "• Discover synonyms\n"
        "• Count words and characters\n"
        "• Format text quickly\n\n"
        "🔒 *Privacy:* I don't store your messages. "
        "Everything is processed in memory and discarded.\n\n"
        "⚠️ I do not use any external paid APIs or scrape third-party services. "
        "All suggestions are rule-based."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def rewrite_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/rewrite <your text>`\nExample: `/rewrite I can't attend the meeting`",
            parse_mode="Markdown",
        )
        return
    text = " ".join(args)
    context.user_data["pending_text"] = text
    context.user_data["action"] = "rewrite"

    keyboard = [
        [
            InlineKeyboardButton("Formal", callback_data="tone_formal"),
            InlineKeyboardButton("Casual", callback_data="tone_casual"),
            InlineKeyboardButton("Confident", callback_data="tone_confident"),
        ]
    ]
    await update.message.reply_text(
        f"Choose a tone for:\n\n_{text}_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def synonyms_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/synonyms <word>`\nExample: `/synonyms happy`",
            parse_mode="Markdown",
        )
        return
    word = args[0]
    syns = get_synonyms(word)
    if syns:
        await update.message.reply_text(
            f"*Synonyms for* `{word}`:\n• " + "\n• ".join(syns),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"Sorry, I don't have synonyms for `{word}` yet.\n"
            "Try common words like: good, bad, happy, sad, big, small, fast, smart, beautiful.",
            parse_mode="Markdown",
        )


async def count_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/count <text>`\nExample: `/count Hello world. How are you?`",
            parse_mode="Markdown",
        )
        return
    text = " ".join(args)
    words, chars, chars_ns, sentences = count_text(text)
    await update.message.reply_text(
        f"📊 *Text Statistics*\n\n"
        f"Words: *{words}*\n"
        f"Characters (with spaces): *{chars}*\n"
        f"Characters (no spaces): *{chars_ns}*\n"
        f"Sentences: *{sentences}*",
        parse_mode="Markdown",
    )


async def format_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: `/format <text>`\nI'll ask you which format you want.",
            parse_mode="Markdown",
        )
        return
    text = " ".join(args)
    context.user_data["pending_text"] = text

    keyboard = [
        [
            InlineKeyboardButton("UPPER", callback_data="fmt_upper"),
            InlineKeyboardButton("lower", callback_data="fmt_lower"),
        ],
        [
            InlineKeyboardButton("Title Case", callback_data="fmt_title"),
            InlineKeyboardButton("Sentence case", callback_data="fmt_sentence"),
        ],
        [
            InlineKeyboardButton("Reverse", callback_data="fmt_reverse"),
        ],
    ]
    await update.message.reply_text(
        f"Choose a format for:\n\n_{text}_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ---------- Plain text handler ----------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
    context.user_data["pending_text"] = text
    words, chars, chars_ns, sentences = count_text(text)

    keyboard = [
        [
            InlineKeyboardButton("Rewrite", callback_data="menu_rewrite"),
            InlineKeyboardButton("Format", callback_data="menu_format"),
        ],
        [
            InlineKeyboardButton("Count", callback_data="menu_count"),
        ],
    ]
    await update.message.reply_text(
        f"Got it! 📝\n\n"
        f"Words: *{words}* | Chars: *{chars}* | Sentences: *{sentences}*\n\n"
        "What would you like to do?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ---------- Callback query handler ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    text = context.user_data.get("pending_text", "")

    if data.startswith("tone_"):
        tone = data.replace("tone_", "")
        if not text:
            await query.edit_message_text("No text found. Please send text again.")
            return
        result = rewrite_text(text, tone)
        await query.edit_message_text(
            f"*{tone.capitalize()} version:*\n\n{result}\n\n"
            "_Note: rule-based rewrite, not a full AI._",
            parse_mode="Markdown",
        )

    elif data == "menu_rewrite":
        if not text:
            await query.edit_message_text("Please send text first.")
            return
        keyboard = [
            [
                InlineKeyboardButton("Formal", callback_data="tone_formal"),
                InlineKeyboardButton("Casual", callback_data="tone_casual"),
                InlineKeyboardButton("Confident", callback_data="tone_confident"),
            ]
        ]
        await query.edit_message_text(
            f"Choose a tone for:\n\n_{text}_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data == "menu_format":
        if not text:
            await query.edit_message_text("Please send text first.")
            return
        keyboard = [
            [
                InlineKeyboardButton("UPPER", callback_data="fmt_upper"),
                InlineKeyboardButton("lower", callback_data="fmt_lower"),
            ],
            [
                InlineKeyboardButton("Title Case", callback_data="fmt_title"),
                InlineKeyboardButton("Sentence case", callback_data="fmt_sentence"),
            ],
            [InlineKeyboardButton("Reverse", callback_data="fmt_reverse")],
        ]
        await query.edit_message_text(
            f"Choose a format for:\n\n_{text}_",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

    elif data == "menu_count":
        if not text:
            await query.edit_message_text("Please send text first.")
            return
        words, chars, chars_ns, sentences = count_text(text)
        await query.edit_message_text(
            f"📊 *Text Statistics*\n\n"
            f"Words: *{words}*\n"
            f"Characters (with spaces): *{chars}*\n"
            f"Characters (no spaces): *{chars_ns}*\n"
            f"Sentences: *{sentences}*",
            parse_mode="Markdown",
        )

    elif data.startswith("fmt_"):
        mode = data.replace("fmt_", "")
        if not text:
            await query.edit_message_text("No text found. Please send text again.")
            return
        result = format_text(text, mode)
        await query.edit_message_text(
            f"*Formatted ({mode}):*\n\n{result}",
            parse_mode="Markdown",
        )


# ---------- Error handler ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling update:", exc_info=context.error)


# ---------- Main ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about_cmd))
    app.add_handler(CommandHandler("rewrite", rewrite_cmd))
    app.add_handler(CommandHandler("synonyms", synonyms_cmd))
    app.add_handler(CommandHandler("count", count_cmd))
    app.add_handler(CommandHandler("format", format_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("Wordtune Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
