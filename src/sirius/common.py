import asyncio
import datetime
import inspect
import os
import socket
import tempfile
import threading
from enum import Enum
from typing import Callable, Any, Dict

import pytz
import requests
from _decimal import Decimal
from pydantic import BaseModel, ConfigDict

from sirius.constants import EnvironmentVariable
from sirius.exceptions import ApplicationException, SDKClientException, OperationNotSupportedException


class Environment(Enum):
    Production: str = "Production"
    Test: str = "Test"
    Development: str = "Development"
    CI_CD_PIPELINE: str = "CI/CD Pipeline"


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
    model_config = ConfigDict(arbitrary_types_allowed=True)


def get_environmental_variable(environmental_variable: EnvironmentVariable | str) -> str:
    environmental_variable_key: str = environmental_variable.value if isinstance(environmental_variable, EnvironmentVariable) else environmental_variable
    value: str | None = os.getenv(environmental_variable_key)
    if value is None:
        raise ApplicationException(
            f"Environment variable with the key is not available: {environmental_variable_key}")

    return value


def get_environment() -> Environment:
    environment: str | None = os.getenv(EnvironmentVariable.ENVIRONMENT.value)
    try:
        return Environment.Development if environment is None else Environment(environment)
    except ValueError:
        raise ApplicationException(f"Invalid environment variable setup: {environment}")


def is_production_environment() -> bool:
    return Environment.Production == get_environment()


def is_test_environment() -> bool:
    return Environment.Test == get_environment()


# TODO: Create redundancy check (if a test/production environment is identified as development, no authentication is done)
def is_development_environment() -> bool:
    return Environment.Development == get_environment() or is_ci_cd_pipeline_environment()


def is_ci_cd_pipeline_environment() -> bool:
    return Environment.CI_CD_PIPELINE == get_environment()


def get_application_name() -> str:
    return get_environmental_variable(EnvironmentVariable.APPLICATION_NAME)


def threaded(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        thread: threading.Thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def wait_for_all_coroutines(func: Callable) -> Callable:
    if not inspect.iscoroutinefunction(func):
        raise SDKClientException(
            f"Synchronous method used to in asynchronous context: {func.__module__}.{func.__name__}")

    # TODO: Manage Exceptions
    async def wrapper(*args: Any, **kwargs: Any) -> None:
        asyncio.create_task(func(*args, **kwargs))
        await asyncio.wait(  # type: ignore[type-var]
            set(filter(lambda t: ("wait_for_all_coroutines" not in t.get_coro().__qualname__), asyncio.all_tasks())),  # type: ignore[arg-type,union-attr,attr-defined]
            timeout=600)
        return None

    return wrapper


def is_dict_include_another_dict(one_dict: Dict[Any, Any], another_dict: Dict[Any, Any]) -> bool:
    if not all(key in one_dict for key in another_dict):
        return False

    for key, value in one_dict.items():
        if another_dict[key] != value:
            return False

    return True


def get_decimal_str(decimal: Decimal) -> str:
    return "{:,.2f}".format(float(decimal))


def only_in_dev(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> threading.Thread:
        if not is_development_environment():
            raise OperationNotSupportedException("Operation is only permitted in the dev environment")
        return func(*args, **kwargs)

    return wrapper


def get_servers_fqdn() -> str:
    return socket.getfqdn()


def get_timestamp_from_string(timestamp_string: str, timezone_string: str | None = None) -> datetime.datetime:
    timestamp: datetime.datetime = datetime.datetime.strptime(timestamp_string, "%Y-%m-%dT%H:%M:%SZ")
    return timestamp if timezone_string is None else timestamp.replace(tzinfo=pytz.timezone(timezone_string))


def get_new_temp_file_path() -> str:
    return tempfile.NamedTemporaryFile(delete=False).name


def download_file_from_url(url: str) -> str:
    temp_file_path: str = get_new_temp_file_path()
    open(temp_file_path, "wb").write(requests.get(url).content)
    return temp_file_path
