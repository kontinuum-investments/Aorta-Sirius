import pytest

from sirius.communication.discord import Bot, Server, TextChannel, Message


@pytest.mark.asyncio
async def test_send_message() -> None:
    bot: Bot = await Bot.get()
    server: Server = await bot.get_server()
    text_channel: TextChannel = await server.get_text_channel("test")
    message: Message = await text_channel.send_message("test")
    assert message
