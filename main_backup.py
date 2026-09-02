import json
import http.client

from urllib.parse import urlencode
from openai import OpenAI

client = OpenAI()


# -------------------------
# ИНСТРУМЕНТЫ
# -------------------------

def get_crypto_price(coin, currency="usd"):

    connection = http.client.HTTPSConnection(
        "api.coingecko.com",
        timeout=10
    )

    params = urlencode({
        "ids": coin,
        "vs_currencies": currency
    })

    connection.request(
        "GET",
        f"/api/v3/simple/price?{params}",
        headers={
            "Accept": "application/json",
            "User-Agent": "my-ai-agent"
        }
    )

    response = connection.getresponse()

    data = json.loads(response.read())

    if coin not in data:
        return f"Монета {coin} не найдена."

    if currency not in data[coin]:
        return f"Цена {coin} в валюте {currency} не найдена."

    price = data[coin][currency]

    return price



def save_memory(key, value):
    with open("memory.json", "r", encoding="utf-8") as file:
        memory = json.load(file)

    memory.append({
        "key": key,
        "value": value
    })

    with open("memory.json", "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=4)

    return "Информация сохранена."


def read_memory():
    with open("memory.json", "r", encoding="utf-8") as file:
        memory = json.load(file)

    return json.dumps(
        memory,
        ensure_ascii=False,
        indent=2
    )


# -------------------------
# ОПИСАНИЕ ИНСТРУМЕНТОВ
# -------------------------

tools = [
    {
        "type": "function",
        "name": "get_crypto_price",
        "description": "Получает актуальную цену криптовалюты.",
        "parameters": {
            "type": "object",
            "properties": {
                "coin": {
                    "type": "string",
                    "description": "CoinGecko ID криптовалюты. Например bitcoin, ethereum, solana, avalanche-2."
                },
                "currency": {
                    "type": "string",
                    "description": "Валюта цены, например usd или eur."
                }
            },
            "required": ["coin"]
        }
    },

    {
        "type": "function",
        "name": "save_memory",
        "description": "Сохраняет важную информацию о пользователе в постоянную память.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Название сохраняемой информации, например favorite_language."
                },
                "value": {
                    "type": "string",
                    "description": "Значение сохраняемой информации."
                }
            },
            "required": ["key", "value"]
        }
    },

    {
        "type": "function",
        "name": "read_memory",
        "description": "Читает постоянную память агента. Используй, когда пользователь спрашивает, что ты помнишь или знаешь о нём.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


# -------------------------
# ИСТОРИЯ РАЗГОВОРА
# -------------------------
AGENT_INSTRUCTIONS = """
Ты персональный AI-агент.

Правила работы:

1. Отвечай пользователю на русском языке, если он сам не попросил другой язык.

2. Если для ответа нужны актуальные цены криптовалют,
используй инструмент get_crypto_price.
Не выдумывай текущие цены самостоятельно.

3. Если пользователь явно просит что-то запомнить,
используй save_memory.

4. Если пользователь спрашивает, что ты помнишь о нём,
используй read_memory.

5. Используй инструменты только когда они действительно нужны.

6. После использования инструментов объясняй результат
понятным человеческим языком.

7. Если инструмент вернул ошибку, не придумывай данные.
Сообщи пользователю о проблеме.

8. Не выполняй лишние действия.
Старайся решить задачу минимальным количеством шагов.
"""

MAX_AGENT_STEPS = 10

previous_response_id = None


while True:

    user_message = input("\nТы: ")

    if user_message.lower() == "выход":
        print("Агент: Пока!")
        break


    # -------------------------
    # ПЕРВЫЙ ЗАПРОС
    # -------------------------

    request = {
        "model": "gpt-5.6",
        "input": user_message,
        "tools": tools,
        "instructions": AGENT_INSTRUCTIONS
    }


    if previous_response_id is not None:
        request["previous_response_id"] = previous_response_id


    response = client.responses.create(**request)


    # -------------------------
    # AGENT LOOP
    # -------------------------

    for step in range(MAX_AGENT_STEPS):

        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]


        # Если инструменты больше не нужны
        if not tool_calls:
            print("Агент:", response.output_text)
            previous_response_id = response.id

            break


        tool_outputs = []


        # -------------------------
        # ВЫПОЛНЯЕМ TOOLS
        # -------------------------

        for item in tool_calls:

            print(f"[Агент использует: {item.name}]")

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

                    result = get_crypto_price(
                        coin,
                        currency
                    )


                elif item.name == "save_memory":

                    arguments = json.loads(
                        item.arguments
                    )

                    result = save_memory(
                        arguments["key"],
                        arguments["value"]
                    )


                elif item.name == "read_memory":

                    result = read_memory()


                else:

                    result = (
                        f"Неизвестный инструмент: "
                        f"{item.name}"
                    )


            except Exception as error:

                result = (
                    f"Ошибка инструмента "
                    f"{item.name}: {error}"
                )


            print(f"[Результат: {result}]")


            tool_outputs.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": str(result)
            })


        # -------------------------
        # ОТПРАВЛЯЕМ РЕЗУЛЬТАТЫ GPT
        # -------------------------

        response = client.responses.create(
    model="gpt-5.6",
    instructions=AGENT_INSTRUCTIONS,
    previous_response_id=response.id,
    input=tool_outputs,
    tools=tools
)


    else:

        print(
            "Агент: Достигнут лимит "
            "шагов агента."
        )


        # Ищем все вызовы инструментов
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        # -------------------------
        # ЕСЛИ TOOLS НЕ НУЖНЫ
        # -------------------------

        if not tool_calls:

            print("Агент:", response.output_text)
            break

        # -------------------------
        # ВЫПОЛНЯЕМ ВСЕ TOOLS
        # -------------------------

        for item in tool_calls:

            print(f"[Агент использует: {item.name}]")

            try:

                if item.name == "get_crypto_price":

                    arguments = json.loads(item.arguments)

                    coin = arguments["coin"]
                    currency = arguments.get(
                        "currency",
                        "usd"
                    )

                    result = get_crypto_price(
                        coin,
                        currency
                    )


                elif item.name == "save_memory":

                    arguments = json.loads(item.arguments)

                    result = save_memory(
                        arguments["key"],
                        arguments["value"]
                    )


                elif item.name == "read_memory":

                    result = read_memory()


                else:

                    result = (
                        f"Неизвестный инструмент: "
                        f"{item.name}"
                    )


            except Exception as error:

                result = (
                    f"Ошибка при выполнении "
                    f"{item.name}: {error}"
                )


# -------------------------
# ГЛАВНЫЙ ЦИКЛ
# -------------------------

    tool_was_used = False


    # -------------------------
    # ОБРАБОТКА TOOL CALL
    # -------------------------

    for item in response.output:

        if item.type == "function_call":

            tool_was_used = True

            print(f"[Агент использует: {item.name}]")

            if item.name == "get_crypto_price":

                arguments = json.loads(item.arguments)

                coin = arguments["coin"]

                currency = arguments.get("currency", "usd")

                result = get_crypto_price(
                    coin,
                    currency
                )


            elif item.name == "save_memory":

                arguments = json.loads(item.arguments)

                result = save_memory(
                    arguments["key"],
                    arguments["value"]
                )


            elif item.name == "read_memory":

                result = read_memory()


            else:

                result = "Неизвестный инструмент."
