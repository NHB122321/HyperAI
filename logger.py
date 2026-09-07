import logging


logging.basicConfig(
    filename="agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)


def log_tool(tool_name):
    logging.info(
        f"TOOL | {tool_name}"
    )


def log_result(result):
    logging.info(
        f"RESULT | {result}"
    )


def log_error(error):
    logging.error(
        f"ERROR | {error}"
    )

def log_user_message(message):
    logging.info(
        f"USER | {message}"
        
    )
    
def log_assistant_message(message):
    logging.info(
        f"ASSISTANT | {message}"
    )


def log_model_route(mode, model, reason):
    """Помогает понять, почему маршрутизатор выбрал эту модель."""
    logging.info("MODEL | mode=%s | model=%s | reason=%s", mode, model, reason)
