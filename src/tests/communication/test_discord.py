import pytest

from sirius.communication.discord import Bot, Server, RoleType, TextChannel


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
async def test_create_public_text_channel() -> None:
    bot: Bot = await Bot.get()
    server: Server = await bot.get_server()
    text_channel: TextChannel = await server.get_text_channel("test", True)
    assert text_channel is not None
    await text_channel.delete()


@pytest.mark.asyncio
async def test_create_private_text_channel() -> None:
    bot: Bot = await Bot.get()
    server: Server = await bot.get_server()
    text_channel: TextChannel = await server.get_text_channel("test")
    assert text_channel is not None
    await text_channel.delete()
