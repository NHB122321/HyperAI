"""Logs contain only fixed event names, counters and validated review codes."""
import logging
import re

REVIEW_CODES = frozenset({
    "sufficient", "incomplete", "off_topic", "contradiction",
    "missing_caveats", "weak_sources", "stale_sources", "other",
})
_ALLOWED = re.compile(
    r"(?:USER|ASSISTANT|TOOL|RESULT|ERROR|MODEL)"
    r"|RESEARCH calls=[0-9]+ completed=[0-9]+"
    r"|RESEARCH sources=[0-9]+"
    r"|REVIEW action=(?:accept|retry) reason=(?:"
    + "|".join(sorted(REVIEW_CODES | {"invalid_response", "unspecified"}))
    + r")"
)


def install_safe_logging():
    previous_factory = logging.getLogRecordFactory()

    def safe_factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        # Never format arbitrary arguments or exception bodies, including HTTP URLs.
        if not isinstance(record.msg, str) or record.args or not _ALLOWED.fullmatch(record.msg):
            record.msg = "DETAILS OMITTED"
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return record

    logging.setLogRecordFactory(safe_factory)
    for name in ("httpx", "httpx2", "httpcore", "openai", "telegram"):
        logging.getLogger(name).setLevel(logging.WARNING)


install_safe_logging()
logging.basicConfig(
    filename="agent.log", level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s", encoding="utf-8",
)


def log_tool(tool_name):
    logging.info("TOOL")


def log_result(result):
    logging.info("RESULT")


def log_error(error):
    logging.error("ERROR")


def log_user_message(message):
    logging.info("USER")


def log_assistant_message(message):
    logging.info("ASSISTANT")


def log_model_route(mode, model, reason):
    logging.info("MODEL")


def log_review(action, reason_code):
    action = action if action in ("accept", "retry") else "retry"
    if reason_code not in REVIEW_CODES | {"invalid_response"}:
        reason_code = "unspecified"
    logging.info(f"REVIEW action={action} reason={reason_code}")


def log_search(calls, completed):
    logging.info(f"RESEARCH calls={int(calls)} completed={int(completed)}")


def log_sources(count):
    logging.info(f"RESEARCH sources={int(count)}")
