import os
from enum import Enum

from sirius.constants import EnvironmentVariable
from sirius.exceptions import ApplicationException


class Environment(Enum):
    Production: str = "Production"
    Staging: str = "Staging"
    Development: str = "Development"


def get_environmental_variable(key: str) -> str:
    value: str = os.getenv(key)
    if value is None:
        raise ApplicationException(f"Environment variable with the key is not available: {key}")

    return value


def get_environment() -> Environment:
    environment: str = os.getenv(EnvironmentVariable.ENVIRONMENT)
    try:
        return Environment.Development if environment is None else Environment(environment)
    except ValueError:
        raise ApplicationException(f"Invalid environment variable setup: {environment}")