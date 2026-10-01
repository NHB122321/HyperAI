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
@dataclass

class SupervisorReview:
    action: Literal[
        "accept",
        "retry"
    ]
    reason: str
    final_answer: Optional[str] = None

class Supervisor:
    def __init__(self, llm_call: Callable[[str], str]):
        self.llm_call = llm_call

    def decide(
    self,
    user_message: str,
    previous_user_message: str | None = None
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

    def review_result(
        self,
        user_message: str,
        agent_name: str,
        agent_result: str
    ) -> SupervisorReview:
        prompt = f"""

Ты Supervisor системы HyperAI.

Ты поручил задачу специализированному агенту.
Теперь проверь его результат.

Исходный запрос пользователя:

{user_message}

Агент:
{agent_name}

Результат агента:

{agent_result}

Твоя задача:

1. Проверить, отвечает ли результат на запрос пользователя.
2. Проверить, выглядит ли результат достаточным и логичным.
3. Не добавлять факты, которых нет в результате агента.
4. Если результат хороший — сформировать финальный ответ пользователю.
5. Если результат явно недостаточный — выбрать retry.

Ответь ТОЛЬКО JSON.

Если всё хорошо:

{{
    "action": "accept",
    "reason": "краткая причина",
    "final_answer": "готовый ответ пользователю"
}}

Если результат плохой:

{{
    "action": "retry",
    "reason": "краткая причина",
    "final_answer": null
}}
"""

        raw_response = self.llm_call(prompt)

        try:
            data = json.loads(raw_response)

            return SupervisorReview(
                action=data["action"],
                reason=data["reason"],
                final_answer=data.get("final_answer")
            )

        except (json.JSONDecodeError, KeyError):
            return SupervisorReview(
                action="accept",
                reason=(
                    "Не удалось разобрать проверку Supervisor, "
                    "используем результат агента."
                ),
                final_answer=agent_result
            )
        
        
def review_result(
    self,
    user_message: str,
    agent_name: str,
    agent_result: str
) -> SupervisorReview:

    prompt = f"""
Ты Supervisor системы HyperAI.

Ты поручил задачу специализированному агенту.
Теперь проверь его результат.

Исходный запрос пользователя:

{user_message}

Агент:

{agent_name}

Результат агента:

{agent_result}

Твоя задача:

1. Проверить, отвечает ли результат на запрос пользователя.
2. Проверить, достаточно ли информации для ответа.
3. Не добавлять факты, которых нет в результате агента.
4. Сохранять важные оговорки и неопределённость.
5. Если в результате есть ссылки или источники —
   НЕ удаляй их из финального ответа.
6. Не изменяй URL источников и не придумывай новые.
7. По возможности оставляй источник рядом с утверждением,
   которое он подтверждает.
8. Если результат хороший — сформируй понятный
   финальный ответ пользователю.
9. Если результат явно недостаточный — выбери retry.

Ответь ТОЛЬКО JSON.

Если всё хорошо:

{{
    "action": "accept",
    "reason": "краткая причина",
    "final_answer": "готовый ответ пользователю с сохранёнными источниками"
}}

Если результат плохой:

{{
    "action": "retry",
    "reason": "краткая причина",
    "final_answer": null
}}
"""
    

    raw_response = self.llm_call(
        prompt
    )

    try:
        data = json.loads(
            raw_response
        )

        return SupervisorReview(
            action=data["action"],
            reason=data["reason"],
            final_answer=data.get(
                "final_answer"
            )
        )

    except (
        json.JSONDecodeError,
        KeyError
    ):
        return SupervisorReview(
            action="accept",
            reason=(
                "Не удалось разобрать проверку "
                "Supervisor, используем результат агента."
            ),
            final_answer=agent_result
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
