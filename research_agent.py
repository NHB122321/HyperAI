from typing import Callable

from agent_result import AgentResult


class ResearchAgent:
    def __init__(self, llm_call: Callable[[str], str]):
        self.llm_call = llm_call

    def run(self, task: str) -> AgentResult:
        """
        Выполняет исследовательскую задачу.
        """

        prompt = f"""
Ты ResearchAgent системы HyperAI.

Твоя задача — исследовать информацию
по поручению Supervisor.

У тебя есть доступ к веб-поиску.

Если задача касается:
- текущих событий;
- свежих новостей;
- цен;
- рынков;
- информации, которая могла измениться;

используй веб-поиск перед ответом.

Не выдумывай актуальные данные.
Если информация противоречива,
скажи об этом.

Отвечай точно, структурированно
и по существу.

Задача от Supervisor:

{task}
"""

        try:
            answer = self.llm_call(prompt)

            return AgentResult(
                status="ok",
                result=answer,
                source="research"
            )

        except Exception as error:
            return AgentResult(
                status="error",
                error=str(error),
                source="research"
            )