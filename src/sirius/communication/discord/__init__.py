import asyncio
import datetime
import time
from enum import Enum
from logging import Logger
from typing import List, Dict, Any

from sirius import application_performance_monitoring, common
from sirius.application_performance_monitoring import Operation
from sirius.common import DataClass
from sirius.communication.discord import constants
from sirius.communication.discord.exceptions import ServerNotFoundException, DuplicateServersFoundException, RoleNotFoundException
from sirius.constants import EnvironmentVariable
from sirius.exceptions import OperationNotSupportedException
from sirius.http_requests import HTTPModel, AsyncHTTPSession, HTTPResponse

logger: Logger = application_performance_monitoring.get_logger()
AsyncHTTPSession(constants.URL, {"Authorization": f"Bot {common.get_environmental_variable(EnvironmentVariable.DISCORD_BOT_TOKEN)}"})


class ServerName(Enum):
    VITA: str = "Vita"
    AURUM: str = "Aurum"
    AORTA: str = "Aorta"


class AortaTextChannels(Enum):
    DEBUG: str = "logs"
    NOTIFICATION: str = "notification"
    BETELGEUSE: str = "betelgeuse"
    WISE: str = "wise"


class RoleType(Enum):
    EVERYONE: str = "@everyone"
    BOT: str = "Bot"
    OTHER: str = ""


class Bot(DataClass):
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
        return await HTTPModel.get_one(cls, constants.ENDPOINT__BOT__GET_BOT)  # type: ignore[return-value]


class Server(DataClass):
    id: int
    name: str
    text_channel_list: List["TextChannel"] = []
    user_list: List["User"] = []
    role_list: List["Role"] = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def get_text_channel(self, text_channel_name: str, is_public_channel: bool = False) -> "TextChannel":
        if len(self.text_channel_list) == 0:
            self.text_channel_list = await TextChannel.get_all(self)

        text_channel_list: List[TextChannel] = list(
            filter(lambda t: t.name == text_channel_name, self.text_channel_list))

        if len(text_channel_list) == 1:
            return text_channel_list[0]
        elif len(text_channel_list) == 0:
            logger.warning("Channel not found; creating channel\n"
                           f"Server Name: {self.name}\n"
                           f"Channel Name: {text_channel_name}\n"
                           )
            text_channel: TextChannel = await TextChannel.create(text_channel_name, self, is_public_channel)
            self.text_channel_list.append(text_channel)
            return text_channel
        else:
            raise DuplicateServersFoundException(f"Duplicate channels found\n"
                                                 f"Server Name: {self.name}\n"
                                                 f"Channel Name: {text_channel_name}\n"
                                                 f"Number of channels: {len(text_channel_list)}\n")

    async def get_user(self, username: str) -> "User":
        self.user_list = await User.get_all(self) if len(self.user_list) == 0 else self.user_list

        try:
            return next(filter(lambda u: u.username == username, self.user_list))
        except StopIteration:
            raise RoleNotFoundException(f"User not found\n"
                                        f"Server Name: {self.name}\n"
                                        f"Username: {username}")

    async def get_server_owner(self) -> "User":
        return await self.get_user(common.get_environmental_variable(EnvironmentVariable.DISCORD_SERVER_OWNER_USERNAME))

    async def get_role(self, role_type: RoleType) -> "Role":
        if role_type == RoleType.OTHER:
            raise OperationNotSupportedException("OTHER Role Type searches are not allowed")

        self.role_list = await Role.get_all(self) if len(self.role_list) == 0 else self.role_list

        try:
            return next(filter(lambda r: r.role_type == role_type, self.role_list))
        except StopIteration:
            raise RoleNotFoundException(f"User not found\n"
                                        f"Server Name: {self.name}\n"
                                        f"Role Type: {role_type.value}")

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Servers")
    async def get_all_servers(cls) -> List["Server"]:
        return await HTTPModel.get_multiple(cls, constants.ENDPOINT__SERVER__GET_ALL_SERVERS)  # type: ignore[return-value]

    @staticmethod
    def get_default_server_name() -> str:
        server_name: str = common.get_application_name()
        return server_name if common.is_production_environment() else f"{server_name} [Dev]"


class User(DataClass):
    id: int
    username: str
    name: str
    is_bot: bool
    server: Server

    @staticmethod
    async def get_all(server: Server) -> List["User"]:
        url: str = constants.ENDPOINT__SERVER__GET_ALL_USERS.replace("$serverID", str(server.id))
        http_session: AsyncHTTPSession = AsyncHTTPSession(url)
        response: HTTPResponse = await http_session.get(url)
        return [User(id=data["user"]["id"],
                     username=data["user"]["username"],
                     name=data["user"]["global_name"],
                     is_bot=data["user"]["bot"] if "bot" in data["user"] else False,
                     server=server) for data in response.data]


class Role(DataClass):
    id: int
    role_type: RoleType
    permissions: str
    server: Server

    @staticmethod
    async def get_all(server: Server) -> List["Role"]:
        role_list: List[Role] = []
        url: str = constants.ENDPOINT__SERVER__GET_ALL_ROLES.replace("$serverID", str(server.id))
        http_session: AsyncHTTPSession = AsyncHTTPSession(url)
        response: HTTPResponse = await http_session.get(url)

        for data in response.data:
            try:
                role_type: RoleType = RoleType(data["name"])
            except ValueError:
                role_type = RoleType.OTHER

            role_list.append(Role(id=data["id"],
                                  role_type=role_type,
                                  permissions=data["permissions"],
                                  server=server))
        return role_list


class Channel(DataClass):
    id: int
    name: str
    type: int

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Channels")
    async def get_all_channels(cls, server: Server) -> List["Channel"]:
        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("<Server_ID>", str(server.id))
        return await HTTPModel.get_multiple(cls, url)  # type: ignore[return-value]

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Create Channel")
    async def create(cls, channel_name: str, server: Server, type_id: int, is_public_channel: bool = False) -> "Channel":
        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("<Server_ID>", str(server.id))
        data: Dict[str, Any] = {"name": channel_name, "type": type_id}

        if not is_public_channel:
            data["permission_overwrites"] = [{
                "id": str((await server.get_server_owner()).id),
                "type": 1,
                "allow": 1024,
                "deny": 0
            }, {
                "id": str((await server.get_role(RoleType.EVERYONE)).id),
                "type": 0,
                "allow": 0,
                "deny": 1024
            }]

        return await HTTPModel.post_return_one(cls, url, data=data)  # type: ignore[return-value]


class TextChannel(Channel):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Send Message")
    async def send_message(self, message: str) -> None:
        if common.is_ci_cd_pipeline_environment():
            return

        url: str = constants.ENDPOINT__CHANNEL__SEND_MESSAGE.replace("<Channel_ID>", str(self.id))
        asyncio.ensure_future(HTTPModel.post_return_one(Message, url, data={"content": message}))

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Get all Text Channels")
    async def get_all(cls, server: Server) -> List["TextChannel"]:
        channel_list: List[Channel] = list(filter(lambda c: c.type == 0, await Channel.get_all_channels(server)))
        return [TextChannel(**channel.model_dump()) for channel in channel_list]

    @classmethod
    @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, "Create a Text Channel")
    async def create(cls, text_channel_name: str, server: Server, type_id: int = 0, is_public_channel: bool = False) -> "TextChannel":
        channel: Channel = await Channel.create(text_channel_name, server, type_id, is_public_channel)
        return TextChannel(**channel.model_dump())

    @staticmethod
    async def get_text_channel_from_default_bot_and_server(text_channel_name: str) -> "TextChannel":
        bot: Bot = await Bot.get()
        server: Server = await bot.get_server()
        return await server.get_text_channel(text_channel_name)


class Message(DataClass):
    id: int
    content: str


def get_timestamp_string(timestamp: datetime.datetime) -> str:
    return f"<t:{str(int(time.mktime(timestamp.timetuple())))}:T>"
