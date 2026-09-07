"""Выбор модели по понятным правилам, без дополнительного запроса к API."""

import re
from dataclasses import dataclass

from config import FAST_MODEL, MODEL_MODE, SMART_MODEL


@dataclass(frozen=True)
class ModelDecision:
    """Результат выбора: модель, режим пользователя и объяснение."""

    model: str
    mode: str
    reason: str


class ModelRouter:
    # Правила ищут действие, а не просто тему: цена BTC и запись расхода простые.
    _COMPLEX_RULES = (
        (
            r"\b(?:проанализ\w*|анализиру\w*|анализ|исследу\w*|обосну\w*|"
            r"докажи\w*|рекомендац\w*|оптимизиру\w*|analy[sz]e|analysis|"
            r"research|investigate|evaluate|recommendations?|optimi[sz]e)\b",
            "Запрошен анализ, исследование или обоснование.",
        ),
        (
            r"\b(?:сравн\w*|сопостав\w*|compare|comparison|contrast)\b",
            "Нужно сравнить варианты или данные.",
        ),
        (
            r"\b(?:спланиру\w*|продум\w*)\b|"
            r"\b(?:состав\w*|разработа\w*|подготов\w*|созда\w*|напиши\w*|придум\w*)\b.{0,80}"
            r"\b(?:план\w*|стратег\w*|архитектур\w*)\b|"
            r"\b(?:create|make|design|build|develop|write)\b.{0,80}"
            r"\b(?:plan|strategy|architecture)\b|"
            r"\bplan\s+(?:my|our|a|an|the|how|to)\b",
            "Нужно разработать план, стратегию или архитектуру.",
        ),
        (
            r"\b(?:сначала|first)\b.+\b(?:затем|потом|после этого|then|next)\b|"
            r"\b(?:пошагов\w*|step.by.step)\b",
            "Запрошено решение в несколько шагов.",
        ),
        (
            r"\b(?:что (?:ты )?можешь сказать|что можно сказать)\b.{0,60}"
            r"\b(?:финанс\w*|расход\w*|доход\w*)\b",
            "Нужны общие выводы о финансовом положении.",
        ),
    )
    _CODE_TOPIC = re.compile(
        r"\b(?:код\w*|программ\w*|функци\w*|скрипт\w*|алгоритм\w*|"
        r"баг\w*|code|program|function|script|algorithm|bugs?)\b"
    )
    _CODE_ACTION = re.compile(
        r"\b(?:напиши\w*|написа\w*|созда\w*|разбери|разберите|разобра\w*|"
        r"объясни\w*|исправ\w*|отлад\w*|реализу\w*|write|create|implement|"
        r"explain|debug|fix|review|refactor)\b"
    )
    # Только короткие продолжения наследуют сложность предыдущего запроса.
    _CONTINUATION = re.compile(
        r"(?:а |и |да,? )?(?:продолжи|продолжай|подробнее|объясни подробнее|"
        r"давай подробнее|почему|а почему|сделай то же самое|"
        r"continue|go on|tell me more|explain more|why|and why|do the same)"
    )

    def __init__(
        self,
        fast_model: str = FAST_MODEL,
        smart_model: str = SMART_MODEL,
        default_mode: str = MODEL_MODE,
    ):
        self.fast_model = self._validate_model(fast_model, "fast_model")
        self.smart_model = self._validate_model(smart_model, "smart_model")
        self.default_mode = self._validate_mode(default_mode)

    @staticmethod
    def _validate_model(model: str, name: str) -> str:
        if not isinstance(model, str) or not model.strip():
            raise ValueError(f"{name} должен содержать имя модели.")
        return model.strip()

    @staticmethod
    def _validate_mode(mode: str) -> str:
        if not isinstance(mode, str) or mode.strip().lower() not in {"auto", "fast", "smart"}:
            raise ValueError("Режим должен быть auto, fast или smart.")
        return mode.strip().lower()

    @classmethod
    def _complexity_reason(cls, text: str) -> str | None:
        normalized = text.casefold()
        if len(text) >= 1600 or len(text.split()) >= 220:
            return "Большой запрос требует обработки большого объёма текста."
        if "```" in text or (
            cls._CODE_TOPIC.search(normalized) and cls._CODE_ACTION.search(normalized)
        ):
            return "Нужно написать, разобрать или исправить код."
        for pattern, reason in cls._COMPLEX_RULES:
            if re.search(pattern, normalized, flags=re.DOTALL):
                return reason
        return None

    @classmethod
    def is_continuation(cls, text: str) -> bool:
        """Короткое уточнение, для которого нужен предыдущий самостоятельный запрос."""
        normalized = text.casefold().strip(" \t\r\n.,!?;:—-…")
        return cls._CONTINUATION.fullmatch(normalized) is not None

    def choose(
        self,
        user_text: str,
        mode: str | None = None,
        previous_user_message: str | None = None,
    ) -> ModelDecision:
        """Ручной режим важнее правил; auto оценивает текущую задачу."""
        if not isinstance(user_text, str):
            raise TypeError("user_text должен быть строкой.")
        selected_mode = self._validate_mode(self.default_mode if mode is None else mode)
        if selected_mode != "auto":
            model = self.fast_model if selected_mode == "fast" else self.smart_model
            return ModelDecision(model, selected_mode, "Модель выбрана ручным режимом.")

        reason = self._complexity_reason(user_text)
        if reason is None and self.is_continuation(user_text):
            if previous_user_message and self._complexity_reason(previous_user_message):
                reason = "Короткое продолжение предыдущей сложной задачи."
        if reason:
            return ModelDecision(self.smart_model, selected_mode, reason)
        return ModelDecision(
            self.fast_model, selected_mode, "Простой запрос: признаков сложной задачи нет."
        )
