import os
import threading
from enum import Enum
from typing import Callable, Any

import rollbar

from sirius import common


class MessageLevel(Enum):
    INFO: str = "info"
    DEBUG: str = "debug"
    WARNING: str = "warning"
    ERROR: str = "error"
    CRITICAL: str = "critical"


rollbar.init(
    access_token=os.getenv("ROLLBAR_ACCESS_TOKEN"),
    environment=common.get_environment().value,
    capture_ip=True,
)


def send_message(message: str, level: MessageLevel) -> None:
    rollbar.report_message(message, level.value)


def report_exception() -> None:
    rollbar.report_exc_info()


def monitored(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            func(*args, **kwargs)
        except Exception as e:
            report_exception()
            raise Exception(e)  # NOSONAR

    return wrapper


def threaded(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        thread: threading.Thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        # logger.debug(f"Thread started for function: {os.path.abspath(inspect.getfile(func))} | {func.__name__}")
        return thread

    return wrapper
