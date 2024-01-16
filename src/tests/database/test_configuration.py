import pytest

from sirius.database import ConfigurationEnum


@pytest.mark.asyncio
async def test_persisted_value_configuration() -> None:
    class TestConfig(ConfigurationEnum):
        TEST_KEY: str = "test_value"

    assert TestConfig.TEST_KEY.value == "value_test"
