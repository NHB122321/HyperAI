import json
import http.client

from urllib.parse import urlencode


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

    data = response.read().decode("utf-8")

    connection.close()

    if response.status != 200:
        return f"Ошибка API: {response.status}"

    data = json.loads(data)

    if coin not in data:
        return f"Монета {coin} не найдена."

    if currency not in data[coin]:
        return (
            f"Цена {coin} в валюте "
            f"{currency} не найдена."
        )

    price = data[coin][currency]

    return price
