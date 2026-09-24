from collections.abc import Callable
import json
from dataclasses import dataclass
from typing import Optional, Literal


SupervisorAction = Literal[
    "direct",
    "tool",
    "delegate"
]


@dataclass
class SupervisorDecision:
    action: SupervisorAction
    target: Optional[str]
    reason: str


class Supervisor:
    def __init__(self, llm_call: Callable[[str], str]):
        self.llm_call = llm_call

    def decide(self, user_message: str) -> SupervisorDecision:

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

Сообщение пользователя:
{user_message}
"""

        raw_response = self.llm_call(prompt)

        try:
            data = json.loads(raw_response)

            return SupervisorDecision(
                action=data["action"],
                target=data.get("target"),
                reason=data["reason"]
            )

        except (json.JSONDecodeError, KeyError):
            return SupervisorDecision(
                action="direct",
                target=None,
                reason="Supervisor не смог разобрать решение модели"
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