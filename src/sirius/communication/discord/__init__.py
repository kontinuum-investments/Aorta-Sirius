from logging import Logger
from typing import Optional, List

import discord
from discord import TextChannel, Client, Guild

from sirius import common, application_performance_monitoring
from sirius.application_performance_monitoring import Operation
from sirius.communication.discord.exceptions import DuplicateServersFoundException, DuplicateChannelsFoundException, ServerNotFoundException
from sirius.constants import EnvironmentVariable

client: Optional[Client] = None
logger: Logger = application_performance_monitoring.get_logger()


@application_performance_monitoring.transaction(Operation.DISCORD, "Send a message")
async def send_message(channel_name: str, message: str) -> None:
    global client
    client = discord.Client(intents=discord.Intents.default())

    @client.event
    async def on_ready() -> None:
        channel: TextChannel = await _get_text_channel(channel_name)
        await channel.send(message)
        await client.close()

    await client.start(common.get_environmental_variable(EnvironmentVariable.DISCORD_BOT_TOKEN), reconnect=True)


async def _get_server() -> Guild:
    global client
    server_name: str = common.get_environmental_variable(EnvironmentVariable.DISCORD_SERVER_NAME)
    if not common.is_production_environment():
        server_name = server_name + " [Dev]"

    guild_list: List[Guild] = list(filter(lambda g: g.name == server_name, client.guilds))

    if len(guild_list) == 1:
        return guild_list[0]
    elif len(guild_list) == 0:
        raise ServerNotFoundException(f"Server not found: {server_name}")
    elif len(guild_list) > 1:
        raise DuplicateServersFoundException(f"{len(guild_list)} servers found for the same server name: {server_name}")


async def _get_text_channel(channel_name: str) -> Optional[TextChannel]:  # type: ignore[return]
    channel_name = channel_name.lower().replace(" ", "-")
    guild: Guild = await _get_server()
    text_channel_list: List[TextChannel] = list(filter(lambda c: c.name == channel_name, guild.text_channels))

    if len(text_channel_list) == 1:
        return text_channel_list[0]
    elif len(text_channel_list) == 0:
        logger.warning(f"Creating a Discord channel\n"
                       f"Server Name: {guild.name}\n"
                       f"Channel Name: {channel_name}")

        return await guild.create_text_channel(channel_name)
    elif len(text_channel_list) > 1:
        raise DuplicateChannelsFoundException(f"{len(text_channel_list)} channels found in the {guild.name} server for the channel name: {channel_name}")
