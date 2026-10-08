"""Проверка веб-поиска и ссылки из метаданных Responses API."""

import logging
from urllib.parse import urlsplit

def format_research_response(response) -> str:
    """Возвращает текст с URL рядом с цитатами или объяснимую ошибку."""
    if response.status != "completed":
        raise ValueError("Исследование не завершено. Попробуй повторить запрос.")

    calls = [item for item in response.output if item.type == "web_search_call"]
    completed = [item for item in calls if item.status == "completed"]
    logging.info("Research web search: calls=%s completed=%s", len(calls), len(completed))
    if not completed:
        raise ValueError("API не подтвердил завершённый веб-поиск. Актуальные данные не проверены.")

    texts = []
    sources = {}  # URL -> название; повторяющиеся источники не дублируются.
    for item in response.output:
        if item.type != "message":
            continue
        for part in item.content:
            if part.type != "output_text":
                continue
            text = part.text
            replacements = []
            for annotation in part.annotations:
                if annotation.type != "url_citation":
                    continue
                url = annotation.url
                parsed = urlsplit(url)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError("API вернул некорректную ссылку на источник.")
                start, end = annotation.start_index, annotation.end_index
                if not 0 <= start <= end <= len(text):
                    raise ValueError("Не удалось сопоставить ссылку с текстом исследования.")
                sources.setdefault(url, annotation.title or url)
                # Обычный URL кликабелен в Telegram без Markdown parse_mode.
                replacements.append((start, end, f" ({url})"))

            # Меняем справа налево, чтобы не сдвигать позиции следующих цитат.
            previous_start = len(text)
            for start, end, replacement in sorted(set(replacements), reverse=True):
                if end > previous_start:
                    raise ValueError("API вернул пересекающиеся цитаты.")
                text = text[:start] + replacement + text[end:]
                previous_start = start
            if text.strip():
                texts.append(text.strip())

    if not texts:
        raise ValueError("Поиск завершился, но текст исследования не получен.")
    if not sources:
        raise ValueError("Поиск выполнялся, но API не вернул цитируемые источники. Попробуй уточнить запрос.")

    logging.info("Research cited sources: %s", len(sources))
    return "\n\n".join(texts)
