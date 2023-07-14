import asyncio
from asyncio import AbstractEventLoop

import pytest

from sirius.communication.discord import Bot, Server, TextChannel, Message


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()


@pytest.mark.asyncio
async def test_send_message() -> None:
    bot: Bot = await Bot.get()
    server: Server = await bot.get_server()
    text_channel: TextChannel = await server.get_text_channel("test")
    message: Message = await text_channel.send_message("test")
    assert message
