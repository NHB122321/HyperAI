import unittest
from unittest.mock import Mock

from agent_result import AgentResult
from research_agent import ResearchAgent
from supervisor import Supervisor


class SupervisorTests(unittest.TestCase):
    def test_malformed_decisions_fall_back_to_direct_and_reviews_retry(self):
        for raw in (None, "", "broken", "null", "[]", "42", "{}",
                    '{"action":[],"reason":"reason"}',
                    '{"action":"unknown","reason":"reason"}',
                    '{"action":"delegate","target":"finance","reason":"reason"}'):
            with self.subTest(raw=raw):
                supervisor = Supervisor(Mock(return_value=raw))
                decision = supervisor.decide("task")
                self.assertEqual((decision.action, decision.target), ("direct", None))
                self.assertEqual(supervisor.review_result("task", "research", "answer").action, "retry")

    def test_invalid_research_payloads_use_error_contract(self):
        for raw in (None, "", "  ", {"answer": "text"}):
            with self.subTest(raw=raw):
                result = ResearchAgent(Mock(return_value=raw)).run("task")
                self.assertEqual(result.status, "error")
                self.assertTrue(result.is_valid())

    def test_research_exception_returns_only_public_message(self):
        result = ResearchAgent(Mock(side_effect=RuntimeError("internal-secret"))).run("task")
        self.assertTrue(result.is_valid())
        self.assertEqual(result.error, "Не удалось завершить поиск. Попробуйте позже.")

    def test_result_contract_rejects_conflicting_or_missing_fields(self):
        for result in (AgentResult("unknown"), AgentResult("ok", " "), AgentResult("error"),
                       AgentResult("ok", "answer", "error"), AgentResult("error", "answer", "error")):
            with self.subTest(result=result):
                self.assertFalse(result.is_valid())
