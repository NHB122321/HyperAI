import unittest
from dataclasses import FrozenInstanceError

from model_router import ModelRouter


class ModelRouterTests(unittest.TestCase):
    def setUp(self):
        self.router = ModelRouter(fast_model="test-fast", smart_model="test-smart", default_mode="auto")

    def test_common_bot_requests_stay_fast(self):
        for message in (
            "Привет!",
            "Я потратил 300 лей на продукты",
            "Какая цена BTC?",
            "Покажи последние заметки",
            "Покажи расходы за месяц",
            "Сколько осталось бюджета на продукты?",
            "Запомни: меня зовут Артём",
            "Удали финансовую операцию 12",
            "Что такое Python?",
            "Show my recent transactions",
            "What is the price of Bitcoin?",
        ):
            with self.subTest(message=message):
                decision = self.router.choose(message)
                self.assertEqual(decision.model, "test-fast")
                self.assertEqual(decision.mode, "auto")
                self.assertTrue(decision.reason)

    def test_complex_task_types_use_smart(self):
        for message in (
            "Проанализируй мои расходы за 3 месяца",
            "Я хочу проанализировать мои расходы за 3 месяца",
            "Составь план обучения Python",
            "Напиши план изучения Python",
            "Разбери этот большой код",
            "Сравни несколько новостей и сделай вывод",
            "Напиши функцию для чтения CSV",
            "Сначала прочитай мои заметки, затем составь список действий",
            "Что можно сказать о моих финансах?",
            "Explain this code",
            "Fix this bug",
            "Create a learning plan for Python",
            "Compare my expenses for July and August",
            "First read my notes, then group them by topic",
            "Помоги: ```python\nx = 1\n```",
            "Текст " * 270,
        ):
            with self.subTest(message=message[:100]):
                self.assertEqual(self.router.choose(message).model, "test-smart")

    def test_manual_mode_overrides_task_complexity(self):
        fast = self.router.choose("Проанализируй мои расходы", mode="fast")
        smart = self.router.choose("Привет", mode="smart")
        self.assertEqual((fast.model, fast.mode), ("test-fast", "fast"))
        self.assertEqual((smart.model, smart.mode), ("test-smart", "smart"))

    def test_default_mode_can_be_overridden(self):
        router = ModelRouter("fast", "smart", default_mode="smart")
        self.assertEqual(router.choose("Привет").model, "smart")
        self.assertEqual(router.choose("Привет", mode="auto").model, "fast")
        self.assertEqual(router.choose("Привет", mode=" AUTO ").mode, "auto")

    def test_only_elliptical_continuations_inherit_complexity(self):
        previous = "Проанализируй расходы за три месяца"
        for continuation in ("Продолжи", "А почему?", "Объясни подробнее", "Tell me more"):
            with self.subTest(continuation=continuation):
                self.assertEqual(
                    self.router.choose(continuation, previous_user_message=previous).model,
                    "test-smart",
                )
        for new_request in ("Привет", "Какая цена BTC?", "Добавь расход 200 лей", "Покажи бюджет"):
            with self.subTest(new_request=new_request):
                self.assertEqual(
                    self.router.choose(new_request, previous_user_message=previous).model,
                    "test-fast",
                )
        self.assertEqual(
            self.router.choose("Подробнее", previous_user_message="Какая цена BTC?").model,
            "test-fast",
        )
        self.assertEqual(self.router.choose("Продолжи").model, "test-fast")

    def test_context_does_not_override_manual_mode(self):
        decision = self.router.choose(
            "Продолжи", mode="fast", previous_user_message="Сравни два месяца"
        )
        self.assertEqual(decision.model, "test-fast")

    def test_invalid_settings_fail_early(self):
        for mode in ("", "premium", None, 123):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    ModelRouter(default_mode=mode)
        for mode in ("", "premium", 123):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    self.router.choose("Привет", mode=mode)
        for name in ("fast_model", "smart_model"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    ModelRouter(**{name: "   "})

    def test_decision_is_immutable(self):
        decision = self.router.choose("Привет")
        with self.assertRaises(FrozenInstanceError):
            decision.model = "different"


if __name__ == "__main__":
    unittest.main()
