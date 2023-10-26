import pytest

from sirius import common
from sirius.azure.key_vault import AzureKeyVault
from sirius.exceptions import SDKClientException


@pytest.mark.asyncio
async def test_secret_crud_operations() -> None:
    key: str = common.get_unique_id(10)

    AzureKeyVault.set(key, "Testing")
    assert AzureKeyVault.get(key) == "Testing"
    AzureKeyVault.delete(key)
    with pytest.raises(SDKClientException):
        AzureKeyVault.get(key)
