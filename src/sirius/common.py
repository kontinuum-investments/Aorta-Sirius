import os
import threading
from enum import Enum
from typing import Callable, Any, Optional

from sirius.constants import EnvironmentVariable
from sirius.exceptions import ApplicationException


class Environment(Enum):
    Production: str = "Production"
    Staging: str = "Staging"
    Development: str = "Development"


def get_environmental_variable(environmental_variable: EnvironmentVariable) -> str:
    value: Optional[str] = os.getenv(environmental_variable.value)
    if value is None:
        raise ApplicationException(f"Environment variable with the key is not available: {environmental_variable.value}")

    return value


def get_environment() -> Environment:
    environment: Optional[str] = os.getenv(EnvironmentVariable.ENVIRONMENT.value)
    try:
        return Environment.Development if environment is None else Environment(environment)
    except ValueError:
        raise ApplicationException(f"Invalid environment variable setup: {environment}")


def is_production_environment() -> bool:
    return Environment.Production == get_environment()


def is_staging_environment() -> bool:
    return Environment.Staging == get_environment()


def is_development_environment() -> bool:
    return Environment.Development == get_environment()


def threaded(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        thread: threading.Thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper
