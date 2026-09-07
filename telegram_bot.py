import os
import asyncio
from pathlib import Path
from config import FAST_MODEL, SMART_MODEL, MODEL_MODE
from model_router import ModelRouter
from voice_tools import transcribe_audio

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

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_ALLOWED_USER_ID = int(
    os.getenv("TELEGRAM_ALLOWED_USER_ID")
)

chat_contexts = {}
# Режим и последний самостоятельный запрос принадлежат конкретному чату.
chat_modes = {}
chat_messages = {}


def describe_mode(mode):
    if mode == "fast":
        return f"fast — {FAST_MODEL}"
    if mode == "smart":
        return f"smart — {SMART_MODEL}"
    return f"auto — {FAST_MODEL} для простых задач, {SMART_MODEL} для сложных"


async def set_model_mode(update: Update, mode: str):
    """Меняем только режим; история диалога остаётся на месте."""
    if not await check_access(update):
        return
    chat_modes[update.effective_chat.id] = mode
    await update.message.reply_text(
        f"Режим: {describe_mode(mode)}.\nИстория разговора сохранена.",
        reply_markup=MAIN_KEYBOARD
    )


async def auto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_model_mode(update, "auto")


async def fast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_model_mode(update, "fast")


async def smart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_model_mode(update, "smart")


async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    mode = chat_modes.get(update.effective_chat.id, MODEL_MODE)
    await update.message.reply_text(
        f"Текущий режим: {describe_mode(mode)}.",
        reply_markup=MAIN_KEYBOARD
    )

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
        "Привет! Я HyperAI 🤖\n"
        "Выбор модели: /auto, /fast, /smart. Текущий режим: /mode.",
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
            await asyncio.to_thread(
                process_message,
                user_message,
                previous_response_id,
                mode=chat_modes.get(chat_id, MODEL_MODE),
                previous_user_message=chat_messages.get(chat_id)
            )
        )

        chat_contexts[chat_id] = (
            new_response_id
        )
        # «Продолжи» не заменяет исходную задачу: следующее «подробнее» тоже её учитывает.
        if not ModelRouter.is_continuation(user_message) or chat_id not in chat_messages:
            chat_messages[chat_id] = user_message

        if not answer.strip():
            answer = "Модель завершила запрос без текстового ответа."

        # Аналитический ответ может быть длиннее лимита одного сообщения Telegram.
        for offset in range(0, len(answer), 4000):
            await update.message.reply_text(
                answer[offset:offset + 4000],
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

    if not await check_access(update):
        return

    chat_id = update.effective_chat.id

    chat_contexts.pop(
        chat_id,
        None
    )
    chat_messages.pop(chat_id, None)

    await update.message.reply_text(
        "Контекст разговора сброшен.",
        reply_markup=MAIN_KEYBOARD
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not await check_access(update):
        return

    await update.message.reply_text(
        "Команды HyperAI:\n\n"
        "/summary — сводка за сегодня\n"
        "/budget — состояние бюджетов\n"
        "/goals — финансовые цели\n"
        "/analyze — анализ месяца\n"
        "/auto — выбирать модель автоматически\n"
        "/fast — быстрая модель\n"
        "/smart — сильная модель\n"
        "/mode — текущий режим\n"
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

    if not await check_access(update):
        return

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

        transcript = await asyncio.to_thread(
            transcribe_audio,
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
    # Команды режима регистрируем так же, как существующие команды бота.
    for command, handler in (
        ("auto", auto_command),
        ("fast", fast_command),
        ("smart", smart_command),
        ("mode", mode_command)
    ):
        application.add_handler(CommandHandler(command, handler))
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
