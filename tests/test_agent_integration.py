"""Проверки маршрутизации и настоящих локальных tools без запросов к API."""

from contextlib import ExitStack, closing
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import call, patch


def response(response_id, output=(), text="Готово"):
    return SimpleNamespace(id=response_id, output=list(output), output_text=text)


def function_call(name, arguments, call_id):
    return SimpleNamespace(
        type="function_call", name=name,
        arguments=json.dumps(arguments, ensure_ascii=False), call_id=call_id,
    )


class AgentIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.import_dir = cls.stack.enter_context(tempfile.TemporaryDirectory())
        cls.stack.enter_context(patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-key-no-network",
            "DATA_DIR": cls.import_dir,
            "FAST_MODEL": "test-fast",
            "SMART_MODEL": "test-smart",
            "MODEL_MODE": "auto",
        }))
        # Импорт logger не должен создавать agent.log в папке проекта.
        cls.stack.enter_context(patch("logging.basicConfig"))
        cls.stack.enter_context(patch("httpx.Client.send", side_effect=AssertionError(
            "Интеграционные тесты не должны обращаться к сети"
        )))
        cls.stack.enter_context(patch("httpx2.Client.send", side_effect=AssertionError(
            "OpenAI SDK не должен обращаться к сети"
        )))
        cls.stack.enter_context(patch("http.client.HTTPSConnection.request", side_effect=AssertionError(
            "Криптовалютные tools не должны обращаться к сети"
        )))
        cls.stack.enter_context(patch.dict(sys.modules))
        for name in (
            "HyperAI", "config", "model_router", "finance_tools",
            "memory_tools", "logger",
        ):
            sys.modules.pop(name, None)
        cls.agent = importlib.import_module("HyperAI")
        cls.finance = importlib.import_module("finance_tools")
        cls.memory = importlib.import_module("memory_tools")
        cls.config = importlib.import_module("config")
        cls.addClassCleanup(cls.agent.client.close)

    def setUp(self):
        self.data_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(self.finance, "DB_FILE", self.data_dir / "finance.db"))
        self.enterContext(patch.object(self.memory, "MEMORY_FILE", self.data_dir / "memory.json"))
        self.create = self.enterContext(patch.object(self.agent.client.responses, "create"))
        self.enterContext(patch("builtins.print"))

    def test_auto_routes_simple_and_complex_requests_and_preserves_return_contract(self):
        for message, expected_model in (
            ("Привет", self.config.FAST_MODEL),
            ("Проанализируй расходы за три месяца", self.config.SMART_MODEL),
        ):
            with self.subTest(message=message):
                self.create.reset_mock()
                self.create.return_value = response("reply", text="Ответ пользователю")

                result = self.agent.process_message(message)

                self.assertEqual(result, ("Ответ пользователю", "reply"))
                request = self.create.call_args.kwargs
                self.assertEqual(request["model"], expected_model)
                self.assertEqual(request["input"], message)
                self.assertNotIn("previous_response_id", request)
                self.assertIn(self.config.AGENT_INSTRUCTIONS, request["instructions"])
                self.assertIs(request["tools"], self.agent.tools)

    def test_manual_mode_is_chosen_once_and_kept_after_real_memory_tool(self):
        for mode, message, expected_model in (
            ("fast", "Проанализируй мои расходы и запомни результат", self.config.FAST_MODEL),
            ("smart", "Запомни моё имя", self.config.SMART_MODEL),
        ):
            with self.subTest(mode=mode):
                self.create.reset_mock()
                self.create.side_effect = [
                    response("tool-step", [function_call(
                        "save_memory", {"key": "имя", "value": "Артём"}, "save-1"
                    )]),
                    response("finished", text="Запомнил"),
                ]
                with patch.object(
                    self.agent.model_router, "choose", wraps=self.agent.model_router.choose
                ) as choose:
                    result = self.agent.process_message(
                        message, "previous-turn", mode=mode,
                        previous_user_message="Предыдущий вопрос",
                    )

                self.assertEqual(result, ("Запомнил", "finished"))
                choose.assert_called_once()
                first, followup = [item.kwargs for item in self.create.call_args_list]
                self.assertEqual(first["model"], expected_model)
                self.assertEqual(followup["model"], expected_model)
                self.assertEqual(first["previous_response_id"], "previous-turn")
                self.assertEqual(followup["previous_response_id"], "tool-step")
                self.assertEqual(first["instructions"], followup["instructions"])
                self.assertIs(first["tools"], followup["tools"])
                self.assertEqual(followup["input"], [{
                    "type": "function_call_output", "call_id": "save-1",
                    "output": "Информация сохранена.",
                }])
                saved = json.loads(self.memory.MEMORY_FILE.read_text(encoding="utf-8"))
                self.assertEqual(saved[-1], {"key": "имя", "value": "Артём"})

    def test_short_followup_uses_previous_task_for_auto_routing(self):
        self.create.return_value = response("continued")

        self.agent.process_message(
            "Продолжи", "complex-task", mode="auto",
            previous_user_message="Проанализируй расходы за три месяца",
        )

        self.assertEqual(self.create.call_args.kwargs["model"], self.config.SMART_MODEL)
        self.assertEqual(self.create.call_args.kwargs["previous_response_id"], "complex-task")

    def test_finance_tools_keep_writing_and_reading_real_temporary_database(self):
        writes = [
            function_call("add_income", {"amount": 2000, "category": "зарплата"}, "income"),
            function_call("add_expense", {"amount": 300, "category": "продукты"}, "expense"),
            function_call("set_budget", {"category": "продукты", "amount": 900}, "budget"),
            function_call("create_savings_goal", {"name": "Ноутбук", "target_amount": 5000}, "goal"),
            function_call("add_goal_progress", {"name": "Ноутбук", "amount": 500}, "progress"),
        ]
        reads = [
            function_call("get_today_summary", {}, "summary"),
            function_call("get_budget_status", {}, "budgets"),
            function_call("get_savings_goals", {}, "goals"),
            function_call("get_financial_insights", {}, "insights"),
        ]
        self.create.side_effect = [
            response("writes", writes), response("reads", reads),
            response("complete", text="Финансы обновлены"),
        ]

        result = self.agent.process_message("Обнови бюджет и проанализируй финансы", mode="smart")

        self.assertEqual(result, ("Финансы обновлены", "complete"))
        self.assertEqual(self.create.call_count, 3)
        for request in self.create.call_args_list:
            self.assertEqual(request.kwargs["model"], self.config.SMART_MODEL)
        write_results = self.create.call_args_list[1].kwargs["input"]
        read_results = self.create.call_args_list[2].kwargs["input"]
        self.assertEqual([item["call_id"] for item in write_results], [item.call_id for item in writes])
        self.assertEqual([item["call_id"] for item in read_results], [item.call_id for item in reads])
        for item in write_results + read_results:
            self.assertNotIn("Ошибка инструмента", item["output"])
            self.assertNotIn("Неизвестный инструмент", item["output"])
        self.assertIn("300", read_results[0]["output"])
        self.assertIn("900", read_results[1]["output"])
        self.assertIn("Ноутбук", read_results[2]["output"])
        with closing(sqlite3.connect(self.finance.DB_FILE)) as connection:
            self.assertEqual(connection.execute(
                "SELECT type, amount FROM transactions ORDER BY id"
            ).fetchall(), [("income", 2000.0), ("expense", 300.0)])
            self.assertEqual(connection.execute(
                "SELECT category, amount FROM budgets"
            ).fetchall(), [("продукты", 900.0)])
            self.assertEqual(connection.execute(
                "SELECT name, saved_amount FROM savings_goals"
            ).fetchall(), [("Ноутбук", 500.0)])

    def test_memory_read_returns_saved_content_to_model(self):
        self.create.side_effect = [
            response("save", [function_call("save_memory", {"key": "город", "value": "Кишинёв"}, "a")]),
            response("read", [function_call("read_memory", {}, "b")]),
            response("done", text="Ты живёшь в Кишинёве"),
        ]

        self.agent.process_message("Запомни мой город Кишинёв и покажи память", mode="fast")

        output = self.create.call_args_list[2].kwargs["input"][0]
        self.assertEqual(output["call_id"], "b")
        self.assertEqual(json.loads(output["output"]), [{"key": "город", "value": "Кишинёв"}])

    def test_invalid_tool_arguments_return_error_without_writing_finance_record(self):
        self.create.side_effect = [
            response("bad-tool", [function_call("add_expense", {"amount": 300}, "bad")]),
            response("error-explained", text="Уточни категорию"),
        ]

        result = self.agent.process_message("Добавь расход", mode="fast")

        self.assertEqual(result, ("Уточни категорию", "error-explained"))
        self.assertIn("Ошибка инструмента add_expense", self.create.call_args.kwargs["input"][0]["output"])
        with closing(sqlite3.connect(self.finance.DB_FILE)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 0)

    def test_api_failure_does_not_retry_with_another_model(self):
        self.create.side_effect = RuntimeError("Модель недоступна")

        with self.assertRaisesRegex(RuntimeError, "Модель недоступна"):
            self.agent.process_message("Привет", mode="smart")

        self.create.assert_called_once()
        self.assertEqual(self.create.call_args.kwargs["model"], self.config.SMART_MODEL)

    def test_console_exit_finishes_after_one_input_without_starting_second_loop(self):
        with patch("builtins.input", side_effect=["  Выход  "]) as user_input:
            self.agent.run_agent()

        user_input.assert_called_once()
        self.create.assert_not_called()

    def test_console_modes_forward_history_and_keep_substantive_task_between_followups(self):
        complex_task = "Проанализируй расходы за три месяца"
        messages = [
            complex_task, "/fast", "Продолжи", "/smart", "Подробнее",
            "/auto", "Привет", "Почему", "/mode", "выход",
        ]
        replies = [("Ответ", f"response-{index}") for index in range(1, 6)]
        with patch("builtins.input", side_effect=messages) as user_input:
            with patch.object(self.agent, "process_message", side_effect=replies) as process:
                self.agent.run_agent()

        self.assertEqual(user_input.call_count, len(messages))
        self.assertEqual(process.call_args_list, [
            call(complex_task, None, mode="auto", previous_user_message=None),
            call("Продолжи", "response-1", mode="fast", previous_user_message=complex_task),
            call("Подробнее", "response-2", mode="smart", previous_user_message=complex_task),
            call("Привет", "response-3", mode="auto", previous_user_message=complex_task),
            call("Почему", "response-4", mode="auto", previous_user_message="Привет"),
        ])
        self.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
