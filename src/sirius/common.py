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
    AED: str = "AED"
    AUD: str = "AUD"
    BDT: str = "BDT"
    BGN: str = "BGN"
    CAD: str = "CAD"
    CHF: str = "CHF"
    CLP: str = "CLP"
    CNY: str = "CNY"
    CRC: str = "CRC"
    CZK: str = "CZK"
    DKK: str = "DKK"
    EGP: str = "EGP"
    EUR: str = "EUR"
    GBP: str = "GBP"
    GEL: str = "GEL"
    HKD: str = "HKD"
    HUF: str = "HUF"
    IDR: str = "IDR"
    ILS: str = "ILS"
    INR: str = "INR"
    JPY: str = "JPY"
    KES: str = "KES"
    KRW: str = "KRW"
    LKR: str = "LKR"
    MAD: str = "MAD"
    MXN: str = "MXN"
    MYR: str = "MYR"
    NGN: str = "NGN"
    NOK: str = "NOK"
    NPR: str = "NPR"
    NZD: str = "NZD"
    PHP: str = "PHP"
    PKR: str = "PKR"
    PLN: str = "PLN"
    RON: str = "RON"
    SEK: str = "SEK"
    SGD: str = "SGD"
    THB: str = "THB"
    TRY: str = "TRY"
    TZS: str = "TZS"
    UAH: str = "UAH"
    UGX: str = "UGX"
    USD: str = "USD"
    UYU: str = "UYU"
    VND: str = "VND"
    XOF: str = "XOF"
    ZAR: str = "ZAR"


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
