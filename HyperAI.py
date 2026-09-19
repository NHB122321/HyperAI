from datetime import datetime

# Конфигурация загружает .env до импорта модулей с настройками DATA_DIR.
from config import MAX_AGENT_STEPS, AGENT_INSTRUCTIONS
from model_router import ModelRouter

from logger import (
    log_tool,
    log_result,
    log_error,
    log_user_message,
    log_assistant_message,
    log_model_route
)

from finance_tools import (
    init_database,
    add_expense,
    add_income,
    get_today_summary,
    get_recent_transactions,
    delete_transaction,
    update_transaction,
    get_month_summary,
    compare_months,
    get_savings_rate,
    get_category_breakdown,
    set_budget,
    get_budget_status,
    create_savings_goal,
    add_goal_progress,
    get_savings_goals,
    get_financial_insights

)

import json

from openai import OpenAI

from crypto_tools import get_crypto_price

from memory_tools import (
    save_memory,
    read_memory
)

client = OpenAI()
model_router = ModelRouter()



# -------------------------
# ОПИСАНИЕ ИНСТРУМЕНТОВ
# -------------------------

tools = [

    {
        "type": "function",
        "name": "get_crypto_price",
        "description": (
            "Получает актуальную цену "
            "криптовалюты."
        ),
        "parameters": {
            "type": "object",
            "properties": {

                "coin": {
                    "type": "string",
                    "description": (
                        "CoinGecko ID криптовалюты. "
                        "Например bitcoin, ethereum, "
                        "solana, avalanche-2."
                    )
                },

                "currency": {
                    "type": "string",
                    "description": (
                        "Валюта цены, например "
                        "usd или eur."
                    )
                }
            },

            "required": ["coin"]
        }
    }
    ,
    {
        "type": "function",
        "name": "save_memory",
        "description": (
            "Сохраняет важную информацию "
            "о пользователе."
        ),
        "parameters": {
            "type": "object",
            "properties": {

                "key": {
                    "type": "string",
                    "description": (
                        "Название информации."
                    )
                },

                "value": {
                    "type": "string",
                    "description": (
                        "Значение информации."
                    )
                }
            },

            "required": [
                "key",
                "value"
            ]
        }
    }
    ,
    {
        "type": "function",
        "name": "read_memory",
        "description": (
            "Читает постоянную память агента."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
    ,
    {
    "type": "function",
    "name": "add_expense",
    "description": (
        "Записывает расход пользователя в финансовую базу. "
        "Используй, когда пользователь сообщает, что потратил деньги."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "Сумма расхода."
            },
            "category": {
                "type": "string",
                "description": (
                    "Категория расхода, например продукты, "
                    "транспорт, развлечения, жильё."
                )
            },
            "description": {
                "type": "string",
                "description": "Дополнительное описание расхода."
            },
            "currency": {
                "type": "string",
                "description": (
                    "Валюта. Например MDL, USD или EUR. "
                    "Если не указана, используй MDL."
                )
            }
        },
        "required": [
            "amount",
            "category"
        ]
    }
}
,
{
    "type": "function",
    "name": "add_income",
    "description": (
        "Записывает доход пользователя в финансовую базу. "
        "Используй, когда пользователь сообщает, что получил или заработал деньги."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "Сумма дохода."
            },
            "category": {
                "type": "string",
                "description": (
                    "Источник или категория дохода, "
                    "например работа, зарплата, подарок."
                )
            },
            "description": {
                "type": "string",
                "description": "Дополнительное описание дохода."
            },
            "currency": {
                "type": "string",
                "description": (
                    "Валюта. Например MDL, USD или EUR. "
                    "Если не указана, используй MDL."
                )
            }
        },
        "required": [
            "amount",
            "category"
        ]
    }
}
,
{
    "type": "function",
    "name": "get_today_summary",
    "description": (
        "Получает финансовую сводку пользователя "
        "за сегодняшний день: доходы, расходы и разницу."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
,
{
    "type": "function",
    "name": "get_recent_transactions",
    "description": (
        "Показывает последние финансовые операции пользователя."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": (
                    "Количество последних операций. "
                    "По умолчанию 10."
                )
            }
        },
        "required": []
    }
}
,
{
    "type": "function",
    "name": "delete_transaction",
    "description": (
        "Удаляет финансовую операцию по её ID. "
        "Используй только когда пользователь явно просит удалить конкретную операцию."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "transaction_id": {
                "type": "integer",
                "description": "ID финансовой операции."
            }
        },
        "required": ["transaction_id"]
    }
}
,
{
    "type": "function",
    "name": "update_transaction",
    "description": (
        "Редактирует существующую финансовую операцию "
        "по её ID. Можно изменить сумму, категорию, "
        "описание или валюту."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "transaction_id": {
                "type": "integer",
                "description": "ID операции."
            },
            "amount": {
                "type": "number",
                "description": "Новая сумма операции."
            },
            "category": {
                "type": "string",
                "description": "Новая категория."
            },
            "description": {
                "type": "string",
                "description": "Новое описание."
            },
            "currency": {
                "type": "string",
                "description": "Новая валюта."
            }
        },
        "required": [
            "transaction_id"
        ]
    }
}
,
{
    "type": "function",
    "name": "get_month_summary",
    "description": (
        "Получает финансовую сводку за месяц: "
        "доходы, расходы, разницу и категории."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "year": {
                "type": "integer",
                "description": (
                    "Год финансовой сводки. "
                    "Указывай только если пользователь явно назвал год. "
                    "Если год не назван, НЕ спрашивай его и не передавай "
                    "этот параметр: Python автоматически использует текущий год."
                )
            },
            "month": {
                "type": "integer",
                "description": (
                    "Номер месяца от 1 до 12. "
                    "Преобразуй название месяца самостоятельно: "
                    "январь=1, февраль=2, март=3, апрель=4, "
                    "май=5, июнь=6, июль=7, август=8, "
                    "сентябрь=9, октябрь=10, ноябрь=11, декабрь=12."
                )
            },
            "currency": {
                "type": "string",
                "description": (
                    "Валюта финансовой сводки. "
                    "Например MDL, USD или EUR. "
                    "По умолчанию MDL."
                )
            }
        },
        "required": []
    }
}
,
{
    "type": "function",
    "name": "compare_months",
    "description": (
        "Сравнивает финансовые показатели двух месяцев: "
        "доходы, расходы, чистую разницу и процентное изменение."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "month1": {
                "type": "integer",
                "description": (
                    "Первый месяц от 1 до 12."
                )
            },
            "year1": {
                "type": "integer",
                "description": (
                    "Год первого месяца. "
                    "Если пользователь его не назвал, "
                    "используй текущий год."
                )
            },
            "month2": {
                "type": "integer",
                "description": (
                    "Второй месяц от 1 до 12. "
                    "Если не указан, функция сравнит "
                    "с предыдущим месяцем."
                )
            },
            "year2": {
                "type": "integer",
                "description": (
                    "Год второго месяца."
                )
            },
            "currency": {
                "type": "string",
                "description": (
                    "Валюта сравнения. "
                    "По умолчанию MDL."
                )
            }
        },
        "required": []
    }
}
,
{
    "type": "function",
    "name": "get_savings_rate",
    "description": (
        "Рассчитывает сумму и процент сбережений "
        "пользователя за выбранный месяц."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "year": {
                "type": "integer",
                "description": (
                    "Год. Если пользователь его "
                    "не указал, параметр можно не передавать."
                )
            },
            "month": {
                "type": "integer",
                "description": (
                    "Номер месяца от 1 до 12. "
                    "Если не указан, используется текущий месяц."
                )
            },
            "currency": {
                "type": "string",
                "description": (
                    "Валюта расчёта. "
                    "По умолчанию MDL."
                )
            }
        },
        "required": []
    }
}
,
{
    "type": "function",
    "name": "get_category_breakdown",
    "description": (
        "Анализирует расходы пользователя "
        "по категориям за месяц и показывает "
        "суммы и доли в процентах."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "year": {
                "type": "integer"
            },
            "month": {
                "type": "integer"
            },
            "currency": {
                "type": "string",
                "description": "По умолчанию MDL."
            }
        },
        "required": []
    }
}
,
{
    "type": "function",
    "name": "set_budget",
    "description": (
        "Создаёт или изменяет месячный "
        "бюджет для категории расходов."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string"
            },
            "amount": {
                "type": "number"
            },
            "currency": {
                "type": "string"
            }
        },
        "required": [
            "category",
            "amount"
        ]
    }
}
,
{
    "type": "function",
    "name": "get_budget_status",
    "description": (
        "Показывает состояние месячных бюджетов: "
        "лимит, потрачено, остаток и процент использования."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string"
            },
            "year": {
                "type": "integer"
            },
            "month": {
                "type": "integer"
            },
            "currency": {
                "type": "string"
            }
        },
        "required": []
    }
}
,
{
    "type": "function",
    "name": "create_savings_goal",
    "description": (
        "Создаёт финансовую цель пользователя, "
        "например накопить деньги на машину или отпуск."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "target_amount": {
                "type": "number"
            },
            "currency": {
                "type": "string"
            }
        },
        "required": [
            "name",
            "target_amount"
        ]
    }
},
{
    "type": "function",
    "name": "add_goal_progress",
    "description": (
        "Добавляет накопленные деньги "
        "к существующей финансовой цели."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "amount": {
                "type": "number"
            },
            "currency": {
                "type": "string"
            }
        },
        "required": [
            "name",
            "amount"
        ]
    }
}
,
{
    "type": "function",
    "name": "get_savings_goals",
    "description": (
        "Показывает финансовые цели "
        "и прогресс накоплений."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string"
            },
            "currency": {
                "type": "string"
            }
        },
        "required": []
    }
}
,
{
    "type": "function",
    "name": "get_financial_insights",
    "description": (
        "Получает общую финансовую картину "
        "за месяц: доходы, расходы, категории, "
        "бюджеты, сбережения и финансовые цели. "
        "Используй для общего анализа финансов."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "year": {
                "type": "integer"
            },
            "month": {
                "type": "integer"
            },
            "currency": {
                "type": "string"
            }
        },
        "required": []
    }
}

]


# -------------------------
# ВЫПОЛНЕНИЕ ИНСТРУМЕНТА
# -------------------------

def execute_tool(item):

    try:

        if item.name == "get_crypto_price":

            arguments = json.loads(
                item.arguments
            )

            coin = arguments["coin"]

            currency = arguments.get(
                "currency",
                "usd"
            )

            return get_crypto_price(
                coin,
                currency
            )


        elif item.name == "save_memory":

            arguments = json.loads(
                item.arguments
            )

            return save_memory(
                arguments["key"],
                arguments["value"]
            )


        elif item.name == "read_memory":

            return read_memory()


        elif item.name == "add_expense":

            arguments = json.loads(
                item.arguments
            )

            return add_expense(
                amount=arguments["amount"],
                category=arguments["category"],
                description=arguments.get(
                    "description",
                    ""
                ),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )


        elif item.name == "add_income":

            arguments = json.loads(
                item.arguments
            )

            return add_income(
                amount=arguments["amount"],
                category=arguments["category"],
                description=arguments.get(
                    "description",
                    ""
                ),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )

        elif item.name == "get_today_summary":

            return get_today_summary()

        elif item.name == "get_recent_transactions":

            arguments = json.loads(
                item.arguments
            )

            limit = arguments.get(
                "limit",
                10
            )

            return get_recent_transactions(
                limit
            )

        elif item.name == "delete_transaction":

            arguments = json.loads(
                item.arguments
            )

            return delete_transaction(
                arguments["transaction_id"]
            )

        elif item.name == "update_transaction":

            arguments = json.loads(
                item.arguments
            )

            return update_transaction(
                transaction_id=arguments["transaction_id"],
                amount=arguments.get("amount"),
                category=arguments.get("category"),
                description=arguments.get("description"),
                currency=arguments.get("currency")
            )
        elif item.name == "get_month_summary":

            arguments = json.loads(
                item.arguments
            )

            return get_month_summary(
                year=arguments.get("year"),
                month=arguments.get("month"),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )
        elif item.name == "compare_months":

            arguments = json.loads(
                item.arguments
            )

            return compare_months(
                month1=arguments.get("month1"),
                year1=arguments.get("year1"),
                month2=arguments.get("month2"),
                year2=arguments.get("year2"),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )
        
        elif item.name == "get_savings_rate":

            arguments = json.loads(
                item.arguments
            )

            return get_savings_rate(
                year=arguments.get("year"),
                month=arguments.get("month"),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )
        elif item.name == "get_category_breakdown":

            arguments = json.loads(
                item.arguments
            )

            return get_category_breakdown(
                year=arguments.get("year"),
                month=arguments.get("month"),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )
        elif item.name == "set_budget":

            arguments = json.loads(
                item.arguments
            )

            return set_budget(
                category=arguments["category"],
                amount=arguments["amount"],
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )

        elif item.name == "get_budget_status":

            arguments = json.loads(
                item.arguments
            )

            return get_budget_status(
                category=arguments.get("category"),
                year=arguments.get("year"),
                month=arguments.get("month"),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )
        elif item.name == "create_savings_goal":

            arguments = json.loads(
                item.arguments
            )

            return create_savings_goal(
                name=arguments["name"],
                target_amount=arguments[
                    "target_amount"
                ],
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )


        elif item.name == "add_goal_progress":

            arguments = json.loads(
                item.arguments
            )

            return add_goal_progress(
                name=arguments["name"],
                amount=arguments["amount"],
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )


        elif item.name == "get_savings_goals":

            arguments = json.loads(
                item.arguments
            )

            return get_savings_goals(
                name=arguments.get("name"),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )
        elif item.name == "get_financial_insights":

            arguments = json.loads(
                item.arguments
            )

            return get_financial_insights(
                year=arguments.get("year"),
                month=arguments.get("month"),
                currency=arguments.get(
                    "currency",
                    "MDL"
                )
            )
        else:
            return (
                f"Неизвестный инструмент: "
                f"{item.name}"
            )

    except Exception as error:

        return (
            f"Ошибка инструмента "
            f"{item.name}: {error}"
        )


# -------------------------
# ЗАПУСК АГЕНТА
# -------------------------
def process_message(
    user_message,
    previous_response_id=None,
    *,
    mode=None,
    previous_user_message=None
):

    # Один выбор на весь запрос: ответы инструментов получает та же модель.
    decision = model_router.choose(
        user_message,
        mode=mode,
        previous_user_message=previous_user_message
    )
    log_model_route(decision.mode, decision.model, decision.reason)

    init_database()

    # -------------------------
    # ТЕКУЩАЯ ДАТА
    # -------------------------

    now = datetime.now()

    current_date = now.strftime(
        "%d.%m.%Y"
    )

    runtime_instructions = (
        AGENT_INSTRUCTIONS
        + f"\n\nТекущая дата: {current_date}."
        + "\nИспользуй эту дату для понимания "
          "слов 'сегодня', 'вчера', "
          "'этот месяц' и названий месяцев "
          "без указанного года."
    )


    # -------------------------
    # ЛОГИРУЕМ СООБЩЕНИЕ
    # -------------------------

    log_user_message(
        user_message
    )


    # -------------------------
    # ПЕРВЫЙ ЗАПРОС К GPT
    # -------------------------

    request = {
        "model": decision.model,
        "instructions": runtime_instructions,
        "input": user_message,
        "tools": tools
    }


    if previous_response_id is not None:

        request["previous_response_id"] = (
            previous_response_id
        )


    response = client.responses.create(
        **request
    )


    # -------------------------
    # AGENT LOOP
    # -------------------------

    for step in range(
        MAX_AGENT_STEPS
    ):

        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]


        # -------------------------
        # ФИНАЛЬНЫЙ ОТВЕТ
        # -------------------------

        if not tool_calls:

            assistant_message = (
                response.output_text
            )

            log_assistant_message(
                assistant_message
            )

            return (
                assistant_message,
                response.id
            )


        # -------------------------
        # РЕЗУЛЬТАТЫ TOOLS
        # -------------------------

        tool_outputs = []


        for item in tool_calls:

            print(
                f"[Агент использует: "
                f"{item.name}]"
            )

            log_tool(
                item.name
            )


            result = execute_tool(
                item
            )


            print(
                f"[Результат: {result}]"
            )

            log_result(
                result
            )


            tool_outputs.append({
                "type":
                    "function_call_output",

                "call_id":
                    item.call_id,

                "output":
                    str(result)
            })


        # -------------------------
        # ВОЗВРАЩАЕМ TOOL RESULTS GPT
        # -------------------------

        response = client.responses.create(
            model=decision.model,
            instructions=runtime_instructions,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=tools
        )


    # Если агент зациклился

    error_message = (
        "Не удалось завершить задачу: "
        "достигнут лимит шагов агента."
    )

    log_error(
        error_message
    )

    return (
        error_message,
        response.id
    )

def run_agent():
    """Консоль использует тот же process_message, что и Telegram."""
    previous_response_id = None
    previous_user_message = None
    mode = model_router.default_mode

    while True:
        user_message = input("\nТы: ")
        command = user_message.strip().lower()

        if command == "выход":
            print("Агент: Пока!")
            break

        if command in ("/auto", "/fast", "/smart"):
            mode = command[1:]
            print(f"Агент: Режим {mode}. История разговора сохранена.")
            continue

        if command == "/mode":
            print(f"Агент: Текущий режим — {mode}.")
            continue

        answer, previous_response_id = process_message(
            user_message,
            previous_response_id,
            mode=mode,
            previous_user_message=previous_user_message
        )
        if not model_router.is_continuation(user_message) or previous_user_message is None:
            previous_user_message = user_message
        print("Агент:", answer)
