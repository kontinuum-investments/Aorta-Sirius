import json
from typing import Dict

import pytest
from azure.keyvault.keys import KeyVaultKey

from sirius import common
from sirius.azure.key_vault import AzureKeyVault, AzureKeyVaultCryptography
from sirius.exceptions import SDKClientException
from sirius.iam.constants import AUTHENTICATION_KEY_NAME


def test_secret_crud_operations() -> None:
    key_name: str = f"Tests-{common.get_unique_id(10)}"
    value: str = common.get_unique_id(10)

    AzureKeyVault.set(key_name, value)
    assert AzureKeyVault.get(key_name) == value
    AzureKeyVault.delete(key_name)
    with pytest.raises(SDKClientException):
        AzureKeyVault.get(key_name)


@pytest.mark.skip(reason="Azure Key Vault's key operations are not used for now")
def test_key_crud_operations() -> None:
    key_name: str = f"Tests-{common.get_unique_id(10)}"

    AzureKeyVault.create_key(key_name)
    assert isinstance(AzureKeyVault.get_key(key_name), KeyVaultKey)
    AzureKeyVault.delete_key(key_name)
    with pytest.raises(SDKClientException):
        AzureKeyVault.get_key(key_name)


@pytest.mark.skip(reason="Azure Key Vault's key operations are not used for now")
def test_encrypt_and_decrypt_data() -> None:
    data: Dict[str, str] = {"user": "john.doe@outlook.com"}
    encrypted_data: bytes = AzureKeyVaultCryptography.get_encrypted_data(AUTHENTICATION_KEY_NAME, json.dumps(data).encode())
    decrypted_data: Dict[str, str] = json.loads(AzureKeyVaultCryptography.get_decrypted_data(AUTHENTICATION_KEY_NAME, encrypted_data).decode("utf-8"))
    assert data == decrypted_data
