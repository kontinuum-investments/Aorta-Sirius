import asyncio
import datetime
import time
from enum import Enum
from http import HTTPStatus
from logging import Logger
from typing import List, Dict, Any, Union

from pydantic import PrivateAttr

from sirius import application_performance_monitoring, common
from sirius.common import DataClass
from sirius.communication.discord import constants
from sirius.communication.discord.exceptions import ServerNotFoundException, DuplicateServersFoundException, RoleNotFoundException
from sirius.constants import EnvironmentSecret
from sirius.exceptions import OperationNotSupportedException
from sirius.http_requests import AsyncHTTPSession, HTTPResponse, ClientSideException

logger: Logger = application_performance_monitoring.get_logger()
default_bot: Union["Bot", None] = None


class ServerName(Enum):
    VITA: str = "Vita"
    AURUM: str = "Aurum"
    AORTA: str = "Aorta"


class AortaTextChannels(Enum):
    DEBUG: str = "logs"
    NOTIFICATION: str = "notification"
    WISE: str = "wise"


class RoleType(Enum):
    EVERYONE: str = "@everyone"
    BOT: str = "Bot"
    OTHER: str = ""


class DiscordHTTPSession(AsyncHTTPSession):

    async def get(self, url: str, query_params: Dict[str, Any] | None = None, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        try:
            return await super().get(url, query_params, headers)
        except ClientSideException as e:
            http_response: HTTPResponse = e.data["http_response"]

            if http_response.response_code == HTTPStatus.TOO_MANY_REQUESTS:
                time.sleep(http_response.data["retry_after"] + 0.1)
                return await self.get(url, query_params, headers)

            raise e

    async def put(self, url: str, data: Dict[str, Any], headers: Dict[str, Any] | None = None) -> HTTPResponse:
        try:
            return await super().put(url, data, headers)
        except ClientSideException as e:
            http_response: HTTPResponse = e.data["http_response"]

            if http_response.response_code == HTTPStatus.TOO_MANY_REQUESTS:
                await asyncio.sleep(http_response.data["retry_after"] + 0.1)
                return await self.put(url, data, headers)

            raise e

    async def post(self, url: str, data: Dict[str, Any] | None = None, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        try:
            return await super().post(url, data, headers)
        except ClientSideException as e:
            http_response: HTTPResponse = e.data["http_response"]

            if http_response.response_code == HTTPStatus.TOO_MANY_REQUESTS:
                await asyncio.sleep(http_response.data["retry_after"] + 0.1)
                return await self.post(url, data, headers)

            raise e

    async def delete(self, url: str, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        try:
            return await super().delete(url, headers)
        except ClientSideException as e:
            http_response: HTTPResponse = e.data["http_response"]

            if http_response.response_code == HTTPStatus.TOO_MANY_REQUESTS:
                await asyncio.sleep(http_response.data["retry_after"] + 0.1)
                return await self.delete(url, headers)

            raise e


DiscordHTTPSession(constants.URL,
                   {"Authorization": f"Bot {common.get_environmental_secret(EnvironmentSecret.DISCORD_BOT_TOKEN)}"})


class DiscordDefaults(DataClass):

    @staticmethod
    async def send_message(text_channel_name: str, message: str) -> None:
        global default_bot
        default_bot = await Bot.get() if default_bot is None else default_bot
        server: Server = await default_bot.get_server()
        text_channel: TextChannel = await server.get_text_channel(text_channel_name)
        await text_channel.send_message(message)

    @classmethod
    async def notify(cls, message: str) -> None:
        await DiscordDefaults.send_message(AortaTextChannels.NOTIFICATION.value, message)


class Bot(DataClass):
    id: int
    username: str
    name: str
    server_list: List["Server"] = []
    _http_session: DiscordHTTPSession = PrivateAttr()

    @property
    def http_session(self) -> DiscordHTTPSession:
        return self._http_session

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def _initialize(self) -> None:
        for server in await Server.get_all_servers(self):
            if server in self.server_list:
                existing_server: Server = next(filter(lambda s: s.id == server.id, self.server_list))
                existing_server.__dict__.update(**server.model_dump())
            else:
                self.server_list.append(server)

    async def get_server(self, server_name: str | None = None) -> "Server":
        if server_name is None:
            server_name = Server.get_default_server_name()

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

    @staticmethod
    async def get() -> "Bot":
        url: str = constants.ENDPOINT__BOT__GET_BOT
        http_session: DiscordHTTPSession = DiscordHTTPSession(url)
        response: HTTPResponse = await http_session.get(url)

        bot: Bot = Bot.model_construct(id=response.data["id"],
                                       username=response.data["username"],
                                       name=response.data["global_name"])
        bot._http_session = http_session
        await bot._initialize()

        return bot


class Server(DataClass):
    id: int
    name: str
    text_channel_list: List["TextChannel"] = []
    user_list: List["User"] = []
    role_list: List["Role"] = []
    bot: Bot

    @property
    def http_session(self) -> DiscordHTTPSession:
        return self.bot.http_session

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def _initialize(self) -> None:
        for text_channel in await TextChannel.get_all(self):
            if text_channel in self.text_channel_list:
                existing_text_channel: TextChannel = next(filter(lambda t: t.id == text_channel.id, self.text_channel_list))
                existing_text_channel.__dict__.update(**text_channel.model_dump())
            else:
                self.text_channel_list.append(text_channel)

        for user in await User.get_all(self):
            if user in self.user_list:
                existing_user: User = next(filter(lambda u: u.id == user.id, self.user_list))
                existing_user.__dict__.update(user.model_dump())
            else:
                self.user_list.append(user)

        for role in await Role.get_all(self):
            if role in self.role_list:
                existing_role: Role = next(filter(lambda r: r.id == role.id, self.role_list))
                existing_role.__dict__.update(role.model_dump())
            else:
                self.role_list.append(role)

    async def get_text_channel(self, text_channel_name: str, is_public_channel: bool = False) -> "TextChannel":
        text_channel_list: List[TextChannel] = list(filter(lambda t: t.name == text_channel_name, self.text_channel_list))

        if len(text_channel_list) == 1:
            return text_channel_list[0]
        elif len(text_channel_list) == 0:
            logger.warning("Channel not found; creating channel\n"
                           f"Server Name: {self.name}\n"
                           f"Channel Name: {text_channel_name}\n"
                           )
            text_channel: TextChannel = await TextChannel.create(text_channel_name, self, is_public_channel=is_public_channel)
            self.text_channel_list.append(text_channel)
            return text_channel
        else:
            raise DuplicateServersFoundException(f"Duplicate channels found\n"
                                                 f"Server Name: {self.name}\n"
                                                 f"Channel Name: {text_channel_name}\n"
                                                 f"Number of channels: {len(text_channel_list)}\n")

    async def get_user(self, username: str) -> "User":
        username = username.lower()
        self.user_list = await User.get_all(self) if len(self.user_list) == 0 else self.user_list

        try:
            return next(filter(lambda u: u.username == username, self.user_list))
        except StopIteration:
            raise RoleNotFoundException(f"User not found\n"
                                        f"Server Name: {self.name}\n"
                                        f"Username: {username}")

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
    async def get_all_servers(cls, bot: Bot) -> List["Server"]:
        server_list: List[Server] = []
        response: HTTPResponse = await bot.http_session.get(constants.ENDPOINT__SERVER__GET_ALL_SERVERS)

        for data in response.data:
            server: Server = Server.model_construct(id=data["id"],
                                                    name=data["name"])
            server.bot = bot
            await server._initialize()
            server_list.append(server)

        return server_list

    @staticmethod
    def get_default_server_name() -> str:
        server_name: str = common.get_application_name()
        return server_name if common.is_production_environment() else f"{server_name} [Dev]"


class User(DataClass):
    id: int
    username: str
    name: str | None
    is_bot: bool
    server: Server

    @property
    def http_session(self) -> DiscordHTTPSession:
        return self.server.bot.http_session

    @staticmethod
    async def get_all(server: Server) -> List["User"]:
        url: str = constants.ENDPOINT__SERVER__GET_ALL_USERS.replace("$serverID", str(server.id))
        http_session: DiscordHTTPSession = DiscordHTTPSession(url)
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

    @property
    def http_session(self) -> DiscordHTTPSession:
        return self.server.bot.http_session

    @staticmethod
    async def get_all(server: Server) -> List["Role"]:
        role_list: List[Role] = []
        url: str = constants.ENDPOINT__SERVER__GET_ALL_ROLES.replace("$serverID", str(server.id))
        http_session: DiscordHTTPSession = DiscordHTTPSession(url)
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
    server: Server

    @property
    def http_session(self) -> DiscordHTTPSession:
        return self.server.bot.http_session

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    @classmethod
    async def get_all_channels(cls, server: Server) -> List["Channel"]:
        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("$serverID", str(server.id))
        response: HTTPResponse = await server.http_session.get(url)

        return [Channel(id=data["id"],
                        name=data["name"],
                        type=data["type"],
                        server=server) for data in response.data]

    @classmethod
    async def create(cls, channel_name: str, server: Server, type_id: int, is_public_channel: bool = False) -> "Channel":
        url: str = constants.ENDPOINT__CHANNEL__CREATE_CHANNEL_OR_GET_ALL_CHANNELS.replace("$serverID", str(server.id))
        data: Dict[str, Any] = {"name": channel_name, "type": type_id}

        if not is_public_channel:
            data["permission_overwrites"] = [{
                "id": str((await server.get_role(RoleType.EVERYONE)).id),
                "type": 0,
                "allow": 0,
                "deny": 1024
            }]

        response: HTTPResponse = await server.http_session.post(url, data=data)
        return Channel(id=response.data["id"],
                       name=response.data["name"],
                       type=response.data["type"],
                       server=server)


class TextChannel(Channel):

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def send_message(self, message: str) -> None:
        if common.is_ci_cd_pipeline_environment():
            return

        url: str = constants.ENDPOINT__CHANNEL__SEND_MESSAGE.replace("$channelID", str(self.id))
        await self.http_session.post(url, data={"content": message})

    async def delete(self) -> None:
        await self.http_session.delete(constants.ENDPOINT__CHANNEL__DELETE.replace("$channelID", str(self.id)))
        self.server.text_channel_list.remove(self)

    @classmethod
    async def get_all(cls, server: Server) -> List["TextChannel"]:
        text_channel_list: List[TextChannel] = []
        channel_list: List[Channel] = list(filter(lambda c: c.type == 0, await Channel.get_all_channels(server)))

        for channel in channel_list:
            text_channel: TextChannel = TextChannel.model_construct(**channel.model_dump(exclude={"server"}))
            text_channel.server = server
            text_channel_list.append(text_channel)

        return text_channel_list

    @classmethod
    async def create(cls, text_channel_name: str, server: Server, type_id: int = 0, is_public_channel: bool = False) -> "TextChannel":
        channel: Channel = await Channel.create(text_channel_name, server, type_id, is_public_channel)
        text_channel: TextChannel = TextChannel.model_construct(**channel.model_dump(exclude={"server"}))
        text_channel.server = server
        return text_channel


class Message(DataClass):
    id: int
    content: str


def get_timestamp_string(timestamp: datetime.datetime | datetime.date) -> str:
    return f"<t:{str(int(time.mktime(timestamp.timetuple())))}:T>"
