import pytest

from sirius.communication import sms
from sirius.communication.discord import Bot, Server, RoleType


@pytest.mark.asyncio
async def test_get_user() -> None:
    bot: Bot = await Bot.get()
    server: Server = await bot.get_server(Server.get_default_server_name())
    assert await server.get_user("k_ca") is not None


@pytest.mark.asyncio
async def test_get_role() -> None:
    bot: Bot = await Bot.get()
    server: Server = await bot.get_server(Server.get_default_server_name())
    assert await server.get_role(RoleType.EVERYONE) is not None


@pytest.mark.asyncio
async def test_create_private_channel() -> None:
    bot: Bot = await Bot.get()
    server: Server = await bot.get_server(Server.get_default_server_name())
    await server.get_text_channel("test")
