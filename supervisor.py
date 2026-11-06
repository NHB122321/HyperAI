from collections.abc import Callable
import json
from logger import log_review
from dataclasses import dataclass
from typing import Optional, Literal


SupervisorAction = Literal[
    "direct",
    "delegate"
]


@dataclass
class SupervisorDecision:
    action: SupervisorAction
    target: Optional[str]
    reason: str


@dataclass
class SupervisorReview:
    action: Literal[
        "accept",
        "retry"
    ]
    reason: str

class Supervisor:
    def __init__(self, llm_call: Callable[[str], str]):
        self.llm_call = llm_call

    def decide(
        self,
        user_message: str,
        previous_user_message: str | None = None,
    ) -> SupervisorDecision:
        prompt = f"""

Ты главный агент HyperAI.

Твоя задача — определить, как обработать сообщение пользователя.

Сейчас доступны только два варианта:

1. direct
Используй, если HyperAI может ответить самостоятельно
без поиска актуальной информации.

2. delegate
Используй, если нужен поиск или исследование
актуальной информации.
В таком случае target должен быть "research".

Ответь ТОЛЬКО JSON.

Формат:

{{
    "action": "direct",
    "target": null,
    "reason": "краткая причина"
}}

или

{{
    "action": "delegate",
    "target": "research",
    "reason": "краткая причина"
}}

Контекст предыдущего запроса пользователя:

{previous_user_message}

Если новый запрос является продолжением предыдущего,
учитывай этот контекст.
Если запрос относится к другой теме — игнорируй его.

Текущий запрос пользователя:
{user_message}
"""

        data = self._parse_response(self.llm_call(prompt))
        if data is not None:
            action = data.get("action")
            target = data.get("target")
            if action == "direct" and target is None:
                return SupervisorDecision("direct", None, data["reason"])
            if action == "delegate" and target == "research":
                return SupervisorDecision("delegate", "research", data["reason"])

        return SupervisorDecision(
            "direct", None, "Supervisor получил некорректное решение модели"
        )

    @staticmethod
    def _parse_response(raw_response: str) -> dict | None:
        try:
            data = json.loads(raw_response)
        except (TypeError, ValueError, RecursionError):
            return None
        if not isinstance(data, dict):
            return None
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return None
        return data

    def review_result(
        self,
        user_message: str,
        agent_name: str,
        agent_result: str
    ) -> SupervisorReview:
        prompt = f"""
Ты Supervisor системы HyperAI.
Проверь результат специализированного агента.

Исходный запрос пользователя:
{user_message}

Агент:
{agent_name}

Результат агента:
{agent_result}

Твоя задача:

1. Проверить, отвечает ли результат на запрос пользователя.
2. Проверить, достаточно ли информации и нет ли явных противоречий.
3. Проверить, сохранены ли необходимые оговорки и неопределённость.
4. Если результат достаточный — выбрать accept.
5. Если результат явно неполный или не отвечает на вопрос — выбрать retry.

Не переписывай результат агента.
Не составляй финальный ответ пользователю.
Не добавляй новые факты.
Оценивай предоставленный текст: не утверждай,
что самостоятельно проверил сайты.

Ответь ТОЛЬКО JSON с полями action, reason и reason_code.
reason_code выбери из sufficient, incomplete, off_topic, contradiction,
missing_caveats, weak_sources, stale_sources, other.
reason_code описывает основную причину решения. Критерии качества остаются прежними.
Причину укажи одним коротким предложением.

Если всё хорошо:
{{
    "action": "accept",
    "reason": "краткая причина"
}}

Если нужна повторная проверка:
{{
    "action": "retry",
    "reason": "краткая причина"
}}
"""
        data = self._parse_response(self.llm_call(prompt))
        if data is not None and data.get("action") in ("accept", "retry"):
            code = data.get("reason_code")
            log_review(data["action"], code if isinstance(code, str) else "unspecified")
            return SupervisorReview(action=data["action"], reason=data["reason"])

        log_review("retry", "invalid_response")
        return SupervisorReview(
            action="retry",
            reason="Supervisor не смог подтвердить результат. Проверь полноту ответа и источники.",
        )


if __name__ == "__main__":
    def llm_call(prompt):
        # Placeholder implementation - replace with actual LLM call
        return '{"action": "direct", "target": null, "reason": "Запрос можно обработать напрямую"}'

    supervisor = Supervisor(llm_call)

    test_messages = [
        "Объясни мне async в Python",
        "Найди последние новости про OpenAI",
        "Как работает список в Python?",
        "Проверь в интернете актуальную цену биткоина",
    ]

    for message in test_messages:
        decision = supervisor.decide(message)

        print("\nЗапрос:", message)
        print("Решение:", decision)
