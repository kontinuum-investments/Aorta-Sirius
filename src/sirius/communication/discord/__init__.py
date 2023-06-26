from abc import abstractmethod
from enum import Enum
from logging import Logger
from typing import List, Optional, Dict, Any

from sirius import application_performance_monitoring, common
from sirius.application_performance_monitoring import Operation
from sirius.communication.discord import constants
from sirius.communication.discord.exceptions import ServerNotFoundException, DuplicateServersFoundException
from sirius.constants import EnvironmentVariable
from sirius.http_requests import HTTPModel, HTTPRequest

logger: Logger = application_performance_monitoring.get_logger()


class ServerName(Enum):
    VITA: str = "Vita"
    AURUM: str = "Aurum"
    AORTA: str = "Aorta"


class DiscordHTTPModel(HTTPModel):
    _headers: Optional[Dict[str, Any]] = {"Authorization": f"Bot {common.get_environmental_variable(EnvironmentVariable.DISCORD_BOT_TOKEN)}"}

    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(**kwargs)


class Bot(DiscordHTTPModel):
    id: int
    username: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get Bot")
    async def get(cls) -> "Bot":
        return await HTTPModel.get_one(cls, constants.ENDPOINT__BOT__GET_BOT)  # type: ignore[return-value, arg-type]


class Server(DiscordHTTPModel):
    id: int
    name: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get Server")
    async def get(cls, bot: Optional[Bot] = None, server: Optional[ServerName] = None) -> "Server":
        if bot is None:
            bot = await Bot.get()

        if server is None:
            server = ServerName(common.get_environmental_variable(EnvironmentVariable.DISCORD_SERVER_NAME))

        server_name: str = server.value if common.is_production_environment() else server.value + " [Dev]"
        server_list: List[Server] = list(filter(lambda s: s.name == server_name, await Server.get_all_servers()))

        if len(server_list) == 1:
            return server_list[0]
        elif len(server_list) == 0:
            raise ServerNotFoundException(f"Server not found\n"
                                          f"Bot Name: {bot.username}\n"
                                          f"Server Name: {server_name}\n")
        else:
            raise DuplicateServersFoundException(f"Duplicate servers found\n"
                                                 f"Bot Name: {bot.username}\n"
                                                 f"Server Name: {server_name}\n"
                                                 f"Number of servers: {len(server_list)}\n")

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Servers")
    async def get_all_servers(cls) -> List["Server"]:
        return await HTTPModel.get_multiple(cls, constants.ENDPOINT__SERVER__GET_ALL_SERVERS)  # type: ignore[return-value, arg-type]


class Channel(DiscordHTTPModel):
    id: int
    name: str
    type: int

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Channels")
    async def get_all_channels(cls, server: Server) -> List["Channel"]:
        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("<Server_ID>", str(server.id))
        return await HTTPModel.get_multiple(cls, url)  # type: ignore[return-value, arg-type]

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Create Channel")
    async def create(cls, channel_name: str, type_id: int, bot: Optional[Bot] = None, server: Optional[Server] = None) -> "Channel":
        if bot is None:
            bot = await Bot.get()

        if server is None:
            server = await Server.get(bot)

        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("<Server_ID>", str(server.id))
        data: Dict[str, Any] = {"name": channel_name, "type": type_id}
        return await HTTPModel.post_return_one(url, data=data)  # type: ignore[return-value]


class TextChannel(Channel):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    async def send_message(self, message: str) -> None:
        url: str = constants.ENDPOINT__CHANNEL__SEND_MESSAGE.replace("<Channel_ID>", str(self.id))
        await HTTPRequest.post(url, data={"content": message}, headers=self._headers)

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get Text Channel")
    async def get(cls, text_channel_name: str, bot: Optional[Bot] = None, server: Optional[Server] = None) -> "TextChannel":
        if bot is None:
            bot = await Bot.get()

        if server is None:
            server = await Server.get(bot)

        text_channel_list: List[TextChannel] = list(filter(lambda t: t.name == text_channel_name, await TextChannel.get_all(server)))

        if len(text_channel_list) == 1:
            return text_channel_list[0]
        elif len(text_channel_list) == 0:
            logger.warning("Channel not found; creating channel\n"
                           f"Bot Name: {bot.username}\n"
                           f"Server Name: {server.name}\n"
                           f"Channel Name: {text_channel_name}\n"
                           )
            return await TextChannel.create(text_channel_name)
        else:
            raise DuplicateServersFoundException(f"Duplicate channels found\n"
                                                 f"Bot Name: {bot.username}\n"
                                                 f"Server Name: {server.name}\n"
                                                 f"Channel Name: {text_channel_name}\n"
                                                 f"Number of channels: {len(text_channel_list)}\n")

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Text Channels")
    async def get_all(cls, server: Optional[Server] = None) -> List["TextChannel"]:
        if server is None:
            server = await Server.get()

        channel_list: List[Channel] = list(filter(lambda c: c.type == 0, await Channel.get_all_channels(server)))
        return [TextChannel(**channel.dict()) for channel in channel_list]

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Create a Text Channel")
    async def create(cls, text_channel_name: str, type_id: int = 0, bot: Optional[Bot] = None, server: Optional[Server] = None) -> "TextChannel":
        channel: Channel = await Channel.create(text_channel_name, type_id)
        return TextChannel(**channel.dict())
