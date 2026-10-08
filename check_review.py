from HyperAI import supervisor

review = supervisor.review_result(
    user_message=(
        "Найди три последние новости о Bitcoin. "
        "Укажи даты публикаций и ссылки."
    ),
    agent_name="ResearchAgent",
    agent_result="Bitcoin — это криптовалюта."
)

print("Решение:", review.action)
print("Причина:", review.reason)

if review.action == "retry":
    print("Тест пройден: неполный ответ отклонён.")
else:
    print("Тест не пройден: неполный ответ принят.")
    