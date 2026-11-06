import io
import logging
import unittest
from unittest.mock import Mock
import logger
from supervisor import Supervisor

class SafeLoggingTests(unittest.TestCase):
    def setUp(self):
        self.output = io.StringIO()
        self.handler = logging.StreamHandler(self.output)
        logging.getLogger().addHandler(self.handler)
        self.addCleanup(logging.getLogger().removeHandler, self.handler)

    def test_http_keys_exception_and_personal_text_are_removed(self):
        secret = "123456:telegram-secret sk-api-secret private-message"
        logging.warning("https://api.telegram.org/bot%s/sendMessage", secret)
        logging.warning(secret)
        try:
            raise RuntimeError(secret)
        except RuntimeError:
            logging.exception("failure %s", secret)
        logger.log_user_message(secret)
        logger.log_assistant_message(secret)
        logger.log_result(secret)
        logger.log_error(secret)
        self.assertNotIn(secret, self.output.getvalue())
        self.assertNotIn("telegram-secret", self.output.getvalue())
        self.assertIn("USER", self.output.getvalue())

    def test_review_logs_code_without_reason_text(self):
        review = Supervisor(Mock(return_value='{"action":"retry","reason":"private-message","reason_code":"weak_sources"}'))
        self.assertEqual(review.review_result("private-message", "research", "text").action, "retry")
        self.assertIn("reason=weak_sources", self.output.getvalue())
        self.assertNotIn("private-message", self.output.getvalue())

    def test_invalid_review_is_distinguishable(self):
        Supervisor(Mock(return_value="invalid")).review_result("task", "research", "text")
        self.assertIn("reason=invalid_response", self.output.getvalue())

    def test_unknown_reason_code_is_not_logged(self):
        logger.log_review("accept", "private-message")
        self.assertIn("action=accept reason=unspecified", self.output.getvalue())
