import pytest

from sirius.communication import sms


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_sms_send_message() -> None:
    await sms.send_message("+", "Hello World")
