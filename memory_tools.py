import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(
    os.getenv(
        "DATA_DIR",
        str(BASE_DIR)
    )
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True
)

MEMORY_FILE = DATA_DIR / "memory.json"


def load_memory():

    if not MEMORY_FILE.exists():

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump([], file)

        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except json.JSONDecodeError:

        return []


def save_memory(key, value):

    memory = load_memory()

    memory.append({
        "key": key,
        "value": value
    })

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=4
        )

    return "Информация сохранена."


def read_memory():

    memory = load_memory()

    return json.dumps(
        memory,
        ensure_ascii=False,
        indent=2
    )