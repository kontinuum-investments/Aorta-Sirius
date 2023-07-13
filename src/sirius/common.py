import os
import threading
from enum import Enum
from typing import Callable, Any, Dict

from pydantic import BaseModel

from sirius.constants import EnvironmentVariable
from sirius.exceptions import ApplicationException


class Environment(Enum):
    Production: str = "Production"
    Staging: str = "Staging"
    Development: str = "Development"


class Currency(Enum):
    USD: str = "USD"
    SGD: str = "SGD"
    AUD: str = "AUD"
    NZD: str = "NZD"
    LKR: str = "LKR"
    GBP: str = "GBP"
    EUR: str = "EUR"
    HUF: str = "HUF"


class DataClass(BaseModel):
    class Config:
        arbitrary_types_allowed: bool = True


def get_environmental_variable(environmental_variable: EnvironmentVariable) -> str:
    value: str | None = os.getenv(environmental_variable.value)
    if value is None:
        raise ApplicationException(f"Environment variable with the key is not available: {environmental_variable.value}")

    return value


def get_environment() -> Environment:
    environment: str | None = os.getenv(EnvironmentVariable.ENVIRONMENT.value)
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


def is_dict_include_another_dict(one_dict: Dict[Any, Any], another_dict: Dict[Any, Any]) -> bool:
    if not all(key in one_dict for key in another_dict):
        return False

    for key, value in one_dict.items():
        if another_dict[key] != value:
            return False

    return True
