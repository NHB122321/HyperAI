import os
from pathlib import Path
from voice_tools import transcribe_audio
from dotenv import load_dotenv

from telegram import (
    Update,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from HyperAI import process_message

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_ALLOWED_USER_ID = int(
    os.getenv("TELEGRAM_ALLOWED_USER_ID")
)

chat_contexts = {}

async def check_access(update: Update):

    user_id = update.effective_user.id

    if user_id != TELEGRAM_ALLOWED_USER_ID:

        await update.message.reply_text(
            "⛔ Доступ к HyperAI запрещён."
        )

        return False

    return True

VOICE_DIR = Path("voice_messages")

VOICE_DIR.mkdir(
    exist_ok=True
)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            "📊 Сводка",
            "💰 Бюджеты"
        ],
        [
            "🎯 Цели",
            "📈 Анализ"
        ]
    ],
    resize_keyboard=True
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await check_access(update):
        return


    await update.message.reply_text(
        "Привет! Я HyperAI 🤖",
        reply_markup=MAIN_KEYBOARD
    )


async def ask_hyperai(
    update: Update,
    user_message: str
):

    if not await check_access(update):
        return

    

    chat_id = update.effective_chat.id

    previous_response_id = (
        chat_contexts.get(chat_id)
    )

    try:

        answer, new_response_id = (
            process_message(
                user_message,
                previous_response_id
            )
        )

        chat_contexts[chat_id] = (
            new_response_id
        )

        await update.message.reply_text(
            answer,
            reply_markup=MAIN_KEYBOARD
        )

    except Exception as error:

        print(
            f"Telegram error: {error}"
        )

        await update.message.reply_text(
            "Произошла ошибка при обработке сообщения."
        )


async def summary_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await ask_hyperai(
        update,
        "Покажи мою финансовую сводку за сегодня."
    )


async def goals_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await ask_hyperai(
        update,
        "Покажи мои финансовые цели."
    )


async def budget_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await ask_hyperai(
        update,
        "Покажи состояние всех моих бюджетов."
    )


async def analyze_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await ask_hyperai(
        update,
        "Проанализируй мои финансы за текущий месяц."
    )


async def reset_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat_id = update.effective_chat.id

    chat_contexts.pop(
        chat_id,
        None
    )

    await update.message.reply_text(
        "Контекст разговора сброшен.",
        reply_markup=MAIN_KEYBOARD
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "Команды HyperAI:\n\n"
        "/summary — сводка за сегодня\n"
        "/budget — состояние бюджетов\n"
        "/goals — финансовые цели\n"
        "/analyze — анализ месяца\n"
        "/reset — новый диалог\n"
        "/help — помощь",
        reply_markup=MAIN_KEYBOARD
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_message = update.message.text

    button_messages = {
        "📊 Сводка":
            "Покажи мою финансовую сводку за сегодня.",

        "💰 Бюджеты":
            "Покажи состояние всех моих бюджетов.",

        "🎯 Цели":
            "Покажи мои финансовые цели.",

        "📈 Анализ":
            "Проанализируй мои финансы за текущий месяц."
    }

    user_message = button_messages.get(
        user_message,
        user_message
    )

    await ask_hyperai(
        update,
        user_message
    )

async def handle_voice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    voice = update.message.voice

    telegram_file = await context.bot.get_file(
        voice.file_id
    )

    chat_id = update.effective_chat.id

    file_path = (
        VOICE_DIR
        / f"{chat_id}_{voice.file_unique_id}.ogg"
    )

    try:

        await telegram_file.download_to_drive(
            custom_path=file_path
        )

        await update.message.reply_text(
            "🎙 Распознаю голос..."
        )

        transcript = transcribe_audio(
            file_path
        )

        await update.message.reply_text(
            f"📝 Я услышал:\n{transcript}"
        )

        await ask_hyperai(
            update,
            transcript
        )

    except Exception as error:

        print(
            f"Voice error: {error}"
        )

        await update.message.reply_text(
            "Не удалось обработать голосовое сообщение."
        )

    finally:

        if file_path.exists():

            file_path.unlink()


    user_id = update.effective_user.id

    await update.message.reply_text(
        f"Твой Telegram ID: {user_id}"
    )

def run_telegram_bot():

    if not TELEGRAM_BOT_TOKEN:

        raise ValueError(
            "TELEGRAM_BOT_TOKEN не найден в .env"
        )

    application = (
        Application
        .builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "summary",
            summary_command
        )
    )

    application.add_handler(
        CommandHandler(
            "budget",
            budget_command
        )
    )

    application.add_handler(
        CommandHandler(
            "goals",
            goals_command
        )
    )

    application.add_handler(
        CommandHandler(
            "analyze",
            analyze_command
        )
    )

    application.add_handler(
        CommandHandler(
            "reset",
            reset_command
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )
    application.add_handler(
    MessageHandler(
        filters.VOICE,
        handle_voice
    )
)
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            handle_message
        )
    )

    print(
        "HyperAI Telegram запущен."
    )

   


    application.run_polling()


if __name__ == "__main__":

    run_telegram_bot()