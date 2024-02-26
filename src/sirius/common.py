import base64
import datetime
import io
import multiprocessing
import os
import secrets
import socket
import string
import tempfile
import threading
from _decimal import Decimal
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from typing import Callable, Any, Dict, List

import pytz
import qrcode
import requests
from pydantic import BaseModel, ConfigDict
from qrcode.image.pil import PilImage

from sirius.constants import EnvironmentVariable, EnvironmentSecret
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
    environmental_variable_key: str = environmental_variable.value if isinstance(environmental_variable,
                                                                                 EnvironmentVariable) else environmental_variable
    value: str | None = os.getenv(environmental_variable_key)
    if value is None:
        raise ApplicationException(f"Environment variable with the key is not available: {environmental_variable_key}")

    return value


def get_environmental_secret(environmental_secret: EnvironmentSecret | str) -> str:
    from sirius.azure.key_vault import AzureKeyVault
    environmental_secret_key: str = environmental_secret.value if isinstance(environmental_secret,
                                                                             EnvironmentSecret) else environmental_secret
    return AzureKeyVault.get(environmental_secret_key)


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
    return get_environmental_secret(EnvironmentSecret.APPLICATION_NAME)


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


def get_decimal_str(decimal: Decimal) -> str:
    return "{:,.2f}".format(float(decimal))


def get_date_string(date: datetime.date) -> str:
    return date.strftime("%d/%b/%Y")


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


def get_unique_id(length: int = 16) -> str:
    raw_id: str = "".join(
        secrets.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(length))
    return "-".join([raw_id[i:i + 4] for i in range(0, len(raw_id), 4)])


def run_function_using_multiple_processes(func: Callable, argument_list: List[Any],
                                          maximum_number_of_threads: int | None = None) -> List[Any | None]:
    maximum_number_of_threads = multiprocessing.cpu_count() + 1 if maximum_number_of_threads is None else maximum_number_of_threads
    maximum_number_of_threads = min(maximum_number_of_threads, len(argument_list))

    with ProcessPoolExecutor(max_workers=maximum_number_of_threads) as executor:
        return list(executor.map(func, argument_list))


def get_qr_code(data_str: str) -> str:
    buffered: io.BytesIO = io.BytesIO()
    qr_code: PilImage = qrcode.make(data_str)

    qr_code.save(buffered)
    return base64.b64encode(buffered.getvalue()).decode()


def get_base64_string_from_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode("utf-8")


def get_bytes_from_base64_string(base64_string: str) -> bytes:
    return base64.b64decode(base64_string)


def get_function_documentation(function: Callable) -> Dict[str, Any]:
    return_documentation: str = function.__doc__.replace("\n", "").split("Returns:")[1].strip()
    function_documentation: Dict[str, Any] = {"description": f"Retrieves {return_documentation}",
                                              "arguments": {}}

    for raw_argument_documentation in function.__doc__.split("Returns:")[0].split("Args:")[1].split("\n"):
        if raw_argument_documentation.strip().replace(" ", "") == "":
            continue

        argument_name: str = raw_argument_documentation.strip().split(":")[0].strip().replace(" ", "")
        argument_documentation: str = raw_argument_documentation.strip().split(":")[1].strip()

        if argument_name not in function.__annotations__ or not any(argument_name == a for a in list(function.__annotations__)):
            raise SDKClientException(f"Invalid documentation for the function {function.__name__}")

        function_documentation["arguments"][argument_name] = argument_documentation

    return function_documentation
