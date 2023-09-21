import pytest

from sirius.communication import whatsapp


@pytest.mark.skip(reason="Chargeable")
@pytest.mark.asyncio
async def test_whatsapp_send_message() -> None:
    await whatsapp.send_message("+68645979923", "Hello World")
