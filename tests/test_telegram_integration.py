"""Telegram handlers проверяются без подключения к Telegram или OpenAI."""

from contextlib import ExitStack
import importlib
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch


def make_update(chat_id=100, user_id=42, text="Привет"):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        effective_chat=SimpleNamespace(id=chat_id),
        message=SimpleNamespace(text=text, reply_text=AsyncMock()),
    )


class TelegramIntegrationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.temp_dir = Path(cls.stack.enter_context(tempfile.TemporaryDirectory()))
        cls.stack.enter_context(patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key-no-network",
            "TELEGRAM_BOT_TOKEN": "123456:test-token-no-network",
            "TELEGRAM_ALLOWED_USER_ID": "42",
            "DATA_DIR": str(cls.temp_dir),
            "FAST_MODEL": "test-fast",
            "SMART_MODEL": "test-smart",
            "MODEL_MODE": "auto",
        }))
        cls.stack.enter_context(patch("logging.basicConfig"))
        cls.stack.enter_context(patch("httpx.Client.send", side_effect=AssertionError(
            "Тест не должен обращаться к сети"
        )))
        cls.stack.enter_context(patch("httpx.AsyncClient.send", new_callable=AsyncMock,
                                      side_effect=AssertionError("Тест не должен обращаться к сети")))
        cls.stack.enter_context(patch("httpx2.Client.send", side_effect=AssertionError(
            "OpenAI SDK не должен обращаться к сети"
        )))
        cls.stack.enter_context(patch("httpx2.AsyncClient.send", new_callable=AsyncMock,
                                      side_effect=AssertionError("Тест не должен обращаться к сети")))
        cls.stack.enter_context(patch("http.client.HTTPSConnection.request", side_effect=AssertionError(
            "Криптовалютные tools не должны обращаться к сети"
        )))
        # Существующий voice_messages создаётся относительно текущей папки.
        original_dir = Path.cwd()
        os.chdir(cls.temp_dir)
        cls.stack.callback(os.chdir, original_dir)
        cls.stack.enter_context(patch.dict(sys.modules))
        for name in (
            "telegram_bot", "HyperAI", "config", "model_router", "finance_tools",
            "memory_tools", "logger", "voice_tools",
        ):
            sys.modules.pop(name, None)
        cls.bot = importlib.import_module("telegram_bot")
        cls.config = importlib.import_module("config")
        cls.agent = importlib.import_module("HyperAI")
        cls.addClassCleanup(cls.agent.client.close)
        cls.addClassCleanup(importlib.import_module("voice_tools").client.close)

    def setUp(self):
        self.bot.chat_contexts.clear()
        self.bot.chat_modes.clear()
        self.bot.chat_messages.clear()
        self.process = self.enterContext(patch.object(
            self.bot, "process_message", return_value=("Ответ", "new-response")
        ))
        self.enterContext(patch("builtins.print"))

    async def test_modes_are_per_chat_and_switching_preserves_dialog(self):
        self.bot.chat_contexts.update({100: "history-100", 200: "history-200"})
        self.bot.chat_messages.update({100: "Первый вопрос", 200: "Другой вопрос"})
        update = make_update(100)

        for mode in ("smart", "fast", "auto"):
            with self.subTest(mode=mode):
                await getattr(self.bot, f"{mode}_command")(update, None)
                self.assertEqual(self.bot.chat_modes[100], mode)
                self.assertNotIn(200, self.bot.chat_modes)
                self.assertEqual(self.bot.chat_contexts, {100: "history-100", 200: "history-200"})
                self.assertEqual(self.bot.chat_messages, {100: "Первый вопрос", 200: "Другой вопрос"})
        self.process.assert_not_called()

    async def test_unauthorized_mode_commands_do_not_mutate_chat(self):
        self.bot.chat_modes[100] = "smart"
        self.bot.chat_contexts[100] = "existing-context"
        self.bot.chat_messages[100] = "Вопрос"
        update = make_update(user_id=99)

        for command in ("auto_command", "fast_command", "smart_command", "mode_command"):
            with self.subTest(command=command):
                update.message.reply_text.reset_mock()
                await getattr(self.bot, command)(update, None)
                update.message.reply_text.assert_awaited_once()
                self.assertIn("запрещён", update.message.reply_text.call_args.args[0])
                self.assertEqual(self.bot.chat_modes, {100: "smart"})
                self.assertEqual(self.bot.chat_contexts, {100: "existing-context"})
                self.assertEqual(self.bot.chat_messages, {100: "Вопрос"})
        self.process.assert_not_called()

    async def test_mode_command_reports_default_or_selected_mode_without_model_request(self):
        update = make_update()
        await self.bot.mode_command(update, None)
        self.assertIn(self.config.MODEL_MODE, update.message.reply_text.call_args.args[0])
        self.bot.chat_modes[100] = "smart"
        await self.bot.mode_command(update, None)
        self.assertIn("smart", update.message.reply_text.call_args.args[0])
        self.process.assert_not_called()
        self.assertEqual(self.bot.chat_contexts, {})

    async def test_ask_uses_default_mode_and_updates_successful_history(self):
        update = make_update()

        await self.bot.ask_hyperai(update, "Привет")

        self.process.assert_called_once_with(
            "Привет", None, mode=self.config.MODEL_MODE, previous_user_message=None
        )
        self.assertEqual(self.bot.chat_contexts, {100: "new-response"})
        self.assertEqual(self.bot.chat_messages, {100: "Привет"})
        update.message.reply_text.assert_awaited_once_with(
            "Ответ", reply_markup=self.bot.MAIN_KEYBOARD
        )

    async def test_ask_keeps_chat_context_when_model_changes(self):
        self.bot.chat_contexts.update({100: "old-response", 200: "other-response"})
        self.bot.chat_messages.update({100: "Сложный вопрос", 200: "Другой вопрос"})
        self.bot.chat_modes[200] = "fast"
        update = make_update()
        await self.bot.smart_command(update, None)

        await self.bot.ask_hyperai(update, "Продолжи")

        self.process.assert_called_once_with(
            "Продолжи", "old-response", mode="smart", previous_user_message="Сложный вопрос"
        )
        self.assertEqual(self.bot.chat_contexts[200], "other-response")
        self.assertEqual(self.bot.chat_messages[200], "Другой вопрос")
        self.assertEqual(self.bot.chat_modes[200], "fast")

    async def test_repeated_followups_stay_smart_until_new_simple_task_replaces_anchor(self):
        complex_task = "Проанализируй расходы за три месяца"
        update = make_update()
        self.process.side_effect = self.agent.process_message
        replies = [
            SimpleNamespace(id=f"response-{index}", output=[], output_text="Ответ")
            for index in range(5)
        ]
        messages = [complex_task, "Продолжи", "Подробнее", "Привет", "Почему"]
        with patch.object(self.agent.client.responses, "create", side_effect=replies) as create:
            for index, message in enumerate(messages):
                await self.bot.ask_hyperai(update, message)
                expected_anchor = complex_task if index < 3 else "Привет"
                self.assertEqual(self.bot.chat_messages[100], expected_anchor)

        self.assertEqual([item.kwargs["model"] for item in create.call_args_list], [
            self.config.SMART_MODEL, self.config.SMART_MODEL, self.config.SMART_MODEL,
            self.config.FAST_MODEL, self.config.FAST_MODEL,
        ])
        self.assertEqual([
            item.kwargs.get("previous_response_id") for item in create.call_args_list
        ], [None, "response-0", "response-1", "response-2", "response-3"])
        self.assertEqual(self.bot.chat_contexts[100], "response-4")

    async def test_empty_or_whitespace_model_answer_gets_explicit_nonempty_reply(self):
        for answer in ("", " \n\t "):
            with self.subTest(answer=repr(answer)):
                update = make_update()
                self.process.return_value = (answer, "empty-response")

                await self.bot.ask_hyperai(update, "Привет")

                update.message.reply_text.assert_awaited_once()
                text = update.message.reply_text.call_args.args[0]
                self.assertTrue(text.strip())
                self.assertIn("без текстового ответа", text)
                self.assertEqual(self.bot.chat_contexts[100], "empty-response")

    async def test_failed_request_preserves_last_successful_context_and_message(self):
        self.bot.chat_contexts[100] = "old-response"
        self.bot.chat_messages[100] = "Предыдущий успешный вопрос"
        self.bot.chat_modes[100] = "smart"
        self.process.side_effect = RuntimeError("Модель недоступна")
        update = make_update()

        await self.bot.ask_hyperai(update, "Новый вопрос")

        self.assertEqual(self.bot.chat_contexts, {100: "old-response"})
        self.assertEqual(self.bot.chat_messages, {100: "Предыдущий успешный вопрос"})
        self.assertEqual(self.bot.chat_modes, {100: "smart"})
        self.assertIn("ошибка", update.message.reply_text.call_args.args[0].lower())

    async def test_unauthorized_message_never_reaches_agent(self):
        update = make_update(user_id=99)

        await self.bot.ask_hyperai(update, "Добавь расход 300")

        self.process.assert_not_called()
        self.assertEqual(self.bot.chat_contexts, {})
        self.assertEqual(self.bot.chat_messages, {})

    async def test_long_answer_is_delivered_in_full_as_telegram_sized_messages(self):
        answer = "Развёрнутый ответ. " * 600
        self.process.return_value = (answer, "long-response")
        update = make_update()

        await self.bot.ask_hyperai(update, "Объясни подробно")

        messages = [call.args[0] for call in update.message.reply_text.await_args_list]
        self.assertGreater(len(messages), 1)
        self.assertEqual("".join(messages), answer)
        self.assertTrue(all(0 < len(message) <= 4096 for message in messages))
        self.assertEqual(self.bot.chat_contexts[100], "long-response")

    async def test_unauthorized_voice_is_rejected_before_download_or_transcription(self):
        update = make_update(user_id=99)
        update.message.voice = SimpleNamespace(file_id="voice-id", file_unique_id="unique")
        context = SimpleNamespace(bot=SimpleNamespace(get_file=AsyncMock()))
        with patch.object(self.bot, "transcribe_audio") as transcribe:
            await self.bot.handle_voice(update, context)

        context.bot.get_file.assert_not_awaited()
        transcribe.assert_not_called()
        self.process.assert_not_called()
        self.assertIn("запрещён", update.message.reply_text.call_args.args[0])

    async def test_unauthorized_reset_and_help_preserve_state(self):
        self.bot.chat_contexts[100] = "old-response"
        self.bot.chat_messages[100] = "Успешный вопрос"
        self.bot.chat_modes[100] = "smart"
        for command in ("reset_command", "help_command"):
            with self.subTest(command=command):
                update = make_update(user_id=99)
                await getattr(self.bot, command)(update, None)
                self.assertIn("запрещён", update.message.reply_text.call_args.args[0])
                self.assertEqual(self.bot.chat_contexts, {100: "old-response"})
                self.assertEqual(self.bot.chat_messages, {100: "Успешный вопрос"})
                self.assertEqual(self.bot.chat_modes, {100: "smart"})

    async def test_finance_commands_and_keyboard_still_forward_original_requests(self):
        cases = (
            ("summary_command", "📊 Сводка", "Покажи мою финансовую сводку за сегодня."),
            ("budget_command", "💰 Бюджеты", "Покажи состояние всех моих бюджетов."),
            ("goals_command", "🎯 Цели", "Покажи мои финансовые цели."),
            ("analyze_command", "📈 Анализ", "Проанализируй мои финансы за текущий месяц."),
        )
        self.bot.chat_modes[100] = "fast"
        for command, button, expected in cases:
            with self.subTest(command=command):
                update = make_update(text=button)
                await getattr(self.bot, command)(update, None)
                self.assertEqual(self.process.call_args.args[0], expected)
                self.assertEqual(self.process.call_args.kwargs["mode"], "fast")
                await self.bot.handle_message(update, None)
                self.assertEqual(self.process.call_args.args[0], expected)
                self.assertEqual(self.process.call_args.kwargs["mode"], "fast")
                self.assertIs(update.message.reply_text.call_args.kwargs["reply_markup"], self.bot.MAIN_KEYBOARD)

    async def test_reset_clears_history_and_followup_text_only_for_current_chat(self):
        self.bot.chat_contexts.update({100: "old", 200: "other"})
        self.bot.chat_messages.update({100: "Вопрос", 200: "Другой вопрос"})
        self.bot.chat_modes[100] = "smart"

        await self.bot.reset_command(make_update(), None)

        self.assertEqual(self.bot.chat_contexts, {200: "other"})
        self.assertEqual(self.bot.chat_messages, {200: "Другой вопрос"})
        self.assertEqual(self.bot.chat_modes, {100: "smart"})

    async def test_voice_transcript_uses_selected_mode_and_removes_temporary_audio(self):
        update = make_update()
        update.message.voice = SimpleNamespace(file_id="voice-id", file_unique_id="unique")
        self.bot.chat_modes[100] = "smart"
        telegram_file = SimpleNamespace(download_to_drive=AsyncMock())

        async def download_to_drive(*, custom_path):
            Path(custom_path).write_bytes(b"dummy audio")

        telegram_file.download_to_drive.side_effect = download_to_drive
        context = SimpleNamespace(bot=SimpleNamespace(get_file=AsyncMock(return_value=telegram_file)))
        with patch.object(self.bot, "transcribe_audio", return_value="Проанализируй расходы") as transcribe:
            await self.bot.handle_voice(update, context)

        context.bot.get_file.assert_awaited_once_with("voice-id")
        transcribe.assert_called_once()
        self.assertFalse(Path(transcribe.call_args.args[0]).exists())
        self.process.assert_called_once_with(
            "Проанализируй расходы", None, mode="smart", previous_user_message=None
        )
        self.assertEqual(self.bot.chat_messages[100], "Проанализируй расходы")

    async def test_help_includes_new_and_existing_commands(self):
        update = make_update()

        await self.bot.help_command(update, None)

        text = update.message.reply_text.call_args.args[0]
        for command in ("auto", "fast", "smart", "mode", "summary", "budget", "goals", "analyze", "reset"):
            self.assertIn(f"/{command}", text)

    def test_startup_registers_existing_and_new_handlers(self):
        application = Mock()
        builder = Mock()
        builder.token.return_value.build.return_value = application
        with patch.object(self.bot.Application, "builder", return_value=builder):
            self.bot.run_telegram_bot()

        handlers = [call.args[0] for call in application.add_handler.call_args_list]
        command_names = set()
        for handler in handlers:
            command_names.update(getattr(handler, "commands", ()))
        self.assertTrue({
            "start", "help", "summary", "budget", "goals", "analyze", "reset",
            "auto", "fast", "smart", "mode",
        }.issubset(command_names))
        self.assertIn(self.bot.handle_message, [handler.callback for handler in handlers])
        self.assertIn(self.bot.handle_voice, [handler.callback for handler in handlers])
        application.run_polling.assert_called_once()


if __name__ == "__main__":
    unittest.main()
