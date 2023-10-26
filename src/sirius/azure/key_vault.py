from typing import Dict

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from sirius import common
from sirius.constants import EnvironmentVariable
from sirius.exceptions import SDKClientException

cache: Dict[str, str] = {}


class AzureKeyVault:
    client: SecretClient | None = None

    @classmethod
    def authenticate(cls) -> None:
        if cls.client is not None:
            return

        cls.client = SecretClient(vault_url=common.get_environmental_variable(EnvironmentVariable.AZURE_KEY_VAULT_URL),
                                  credential=DefaultAzureCredential())

    @classmethod
    def get(cls, key: str) -> str:
        global cache
        if key in cache:
            return cache[key]

        cls.authenticate()
        try:
            value: str = cls.client.get_secret(key).value
        except ResourceNotFoundError:
            raise SDKClientException("Secret not found: " + key)

        cache[key] = value
        return value

    @classmethod
    def set(cls, key: str, value: str) -> None:
        cls.authenticate()
        cls.client.set_secret(key, value)

        global cache
        cache[key] = value

    @classmethod
    def delete(cls, key: str) -> None:
        cls.authenticate()
        cls.client.begin_delete_secret(key).result()

        global cache
        if key in cache:
            cache.pop(key)
