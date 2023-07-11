from enum import Enum
from logging import Logger
from typing import List, Dict, Any

from sirius import application_performance_monitoring, common
from sirius.application_performance_monitoring import Operation
from sirius.common import DataClass
from sirius.communication.discord import constants
from sirius.communication.discord.exceptions import ServerNotFoundException, DuplicateServersFoundException
from sirius.constants import EnvironmentVariable
from sirius.http_requests import HTTPModel, HTTPSession

logger: Logger = application_performance_monitoring.get_logger()


class ServerName(Enum):
    VITA: str = "Vita"
    AURUM: str = "Aurum"
    AORTA: str = "Aorta"


class DiscordModel(DataClass):
    _http_session: HTTPSession = HTTPSession(constants.URL, {"Authorization": f"Bot {common.get_environmental_variable(EnvironmentVariable.DISCORD_BOT_TOKEN)}"})


class Bot(DiscordModel):
    id: int
    username: str
    server_list: List["Server"] = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def get_server(self, server_name: str | None = None) -> "Server":
        if server_name is None:
            server_name = Server.get_default_server_name()

        if len(self.server_list) == 0:
            self.server_list = await Server.get_all_servers()

        server_list: List[Server] = list(filter(lambda s: s.name == server_name, self.server_list))

        if len(server_list) == 1:
            return server_list[0]
        elif len(server_list) == 0:
            raise ServerNotFoundException(f"Server not found\n"
                                          f"Bot Name: {self.username}\n"
                                          f"Server Name: {server_name}\n")
        else:
            raise DuplicateServersFoundException(f"Duplicate servers found\n"
                                                 f"Bot Name: {self.username}\n"
                                                 f"Server Name: {server_name}\n"
                                                 f"Number of servers: {len(server_list)}\n")

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get Bot")
    async def get(cls) -> "Bot":
        return await HTTPModel.get_one(cls, cls._http_session, constants.ENDPOINT__BOT__GET_BOT)  # type: ignore[return-value]


class Server(DiscordModel):
    id: int
    name: str
    text_channel_list: List["TextChannel"] = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def get_text_channel(self, text_channel_name: str) -> "TextChannel":
        if len(self.text_channel_list) == 0:
            self.text_channel_list = await TextChannel.get_all(self)

        text_channel_list: List[TextChannel] = list(filter(lambda t: t.name == text_channel_name, self.text_channel_list))

        if len(text_channel_list) == 1:
            return text_channel_list[0]
        elif len(text_channel_list) == 0:
            logger.warning("Channel not found; creating channel\n"
                           f"Server Name: {self.name}\n"
                           f"Channel Name: {text_channel_name}\n"
                           )
            return await TextChannel.create(text_channel_name, self)
        else:
            raise DuplicateServersFoundException(f"Duplicate channels found\n"
                                                 f"Server Name: {self.name}\n"
                                                 f"Channel Name: {text_channel_name}\n"
                                                 f"Number of channels: {len(text_channel_list)}\n")

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Servers")
    async def get_all_servers(cls) -> List["Server"]:
        return await HTTPModel.get_multiple(cls, cls._http_session, constants.ENDPOINT__SERVER__GET_ALL_SERVERS)  # type: ignore[return-value]

    @staticmethod
    def get_default_server_name() -> str:
        server_name: str = common.get_environmental_variable(EnvironmentVariable.DISCORD_SERVER_NAME)
        return server_name if common.is_production_environment() else f"{server_name} [Dev]"


class Channel(DiscordModel):
    id: int
    name: str
    type: int

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Channels")
    async def get_all_channels(cls, server: Server) -> List["Channel"]:
        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("<Server_ID>", str(server.id))
        return await HTTPModel.get_multiple(cls, cls._http_session, url)  # type: ignore[return-value]

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Create Channel")
    async def create(cls, channel_name: str, server: Server, type_id: int) -> "Channel":
        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("<Server_ID>", str(server.id))
        data: Dict[str, Any] = {"name": channel_name, "type": type_id}
        return await HTTPModel.post_return_one(cls, cls._http_session, url, data=data)  # type: ignore[return-value]


class TextChannel(Channel):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Send Message")
    async def send_message(self, message: str) -> "Message":
        url: str = constants.ENDPOINT__CHANNEL__SEND_MESSAGE.replace("<Channel_ID>", str(self.id))
        return await HTTPModel.post_return_one(Message, self._http_session, url, data={"content": message})  # type: ignore[return-value]

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Text Channels")
    async def get_all(cls, server: Server) -> List["TextChannel"]:
        channel_list: List[Channel] = list(filter(lambda c: c.type == 0, await Channel.get_all_channels(server)))
        return [TextChannel(**channel.dict()) for channel in channel_list]

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Create a Text Channel")
    async def create(cls, text_channel_name: str, server: Server, type_id: int = 0) -> "TextChannel":
        channel: Channel = await Channel.create(text_channel_name, server, type_id)
        return TextChannel(**channel.dict())

    @staticmethod
    async def get_text_channel_from_default_bot_and_server(text_channel_name: str) -> "TextChannel":
        bot: Bot = await Bot.get()
        server: Server = await bot.get_server()
        return await server.get_text_channel(text_channel_name)


class Message(DataClass):
    id: int
    content: str
