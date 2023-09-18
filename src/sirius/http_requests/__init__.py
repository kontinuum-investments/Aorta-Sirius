import json
from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, cast

import httpx
from httpx import Response, Cookies, Headers, URL, AsyncClient, Client
from pydantic import BaseModel

from sirius import application_performance_monitoring, common
from sirius.application_performance_monitoring import Operation
from sirius.common import DataClass
from sirius.http_requests.exceptions import ClientSideException, ServerSideException


@dataclass
class HTTPResponse:
    response: Response
    response_code: int
    is_successful: bool
    headers: Headers
    data: Dict[Any, Any] | None = None
    response_text: str | None = None
    cookies: Cookies | None = None

    def __init__(self, response: Response, *args: List[Any], **kwargs: Dict[str, Any]) -> None:
        self.response = response
        self.response_code = self.response.status_code
        self.is_successful = 200 <= self.response_code < 300
        self.response_text = self.response.text
        self.headers = response.headers
        self.cookies = response.cookies

        if self.is_successful and self.response_text is not None and self.response_text != "":
            self.data = self.response.json()

        super().__init__(*args, **kwargs)


class HTTPSession:
    host: str

    @staticmethod
    def raise_http_exception(http_response: HTTPResponse) -> None:
        error_message: str = f"HTTP Exception\n" \
                             f"URL: {str(http_response.response.url)}\n" \
                             f"Headers: {str(http_response.headers)}\n" \
                             f"Method: {http_response.response.request.method.upper()}\n" \
                             f"Response Code: {http_response.response_code}\n" \
                             f"Response Text: {http_response.response_text}"

        if 400 <= http_response.response_code < 500:
            raise ClientSideException(error_message)
        else:
            raise ServerSideException(error_message)


class AsyncHTTPSession(HTTPSession):
    client: AsyncClient
    _instance_list: List["AsyncHTTPSession"] = []

    def __new__(cls, url_str: str, headers: Dict[str, Any] | None = None) -> "AsyncHTTPSession":
        host: str = URL(url_str).host
        instance: AsyncHTTPSession | None = None

        for i in cls._instance_list:
            if i.host == host and (headers is None or common.is_dict_include_another_dict(cast(Dict[str, Any], headers), dict(i.client.headers))):
                instance = i

        if instance is None:
            instance = super().__new__(cls)
            instance.host = host
            instance.client = httpx.AsyncClient()

            if headers is not None:
                instance.client.headers.update(headers)

            cls._instance_list.append(instance)

        if instance.client.is_closed:
            instance.client = httpx.AsyncClient()

        return instance

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "GET")
    async def get(self, url: str, query_params: Dict[str, Any] | None = None, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        http_response: HTTPResponse = HTTPResponse(await self.client.get(url, params=query_params, headers=headers))
        if not http_response.is_successful:
            AsyncHTTPSession.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "PUT")
    async def put(self, url: str, data: Dict[str, Any], headers: Dict[str, Any] | None = None) -> HTTPResponse:
        http_response: HTTPResponse = HTTPResponse(await self.client.put(url, data=data, headers=headers))
        if not http_response.is_successful:
            AsyncHTTPSession.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "POST")
    async def post(self, url: str, data: Dict[str, Any] | None = None, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        data_string: str | None = None
        if data is not None:
            data_string = json.dumps(data)

            if headers is None:
                headers = {}
            headers["content-type"] = "application/json"

        http_response: HTTPResponse = HTTPResponse(await self.client.post(url, data=data_string, headers=headers))  # type: ignore[arg-type]
        if not http_response.is_successful:
            AsyncHTTPSession.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "DELETE")
    async def delete(self, url: str, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        http_response: HTTPResponse = HTTPResponse(await self.client.delete(url, headers=headers))
        if not http_response.is_successful:
            AsyncHTTPSession.raise_http_exception(http_response)

        return http_response


class SyncHTTPSession(HTTPSession):
    _instance_list: List["SyncHTTPSession"] = []
    client: Client
    host: str

    def __new__(cls, url_str: str, headers: Dict[str, Any] | None = None) -> "SyncHTTPSession":
        host: str = URL(url_str).host
        instance: SyncHTTPSession | None = None

        for i in cls._instance_list:
            if i.host == host and (headers is None or common.is_dict_include_another_dict(cast(Dict[str, Any], headers), dict(i.client.headers))):
                instance = i

        if instance is None:
            instance = super().__new__(cls)
            instance.host = host
            instance.client = httpx.Client()

            if headers is not None:
                instance.client.headers.update(headers)

            cls._instance_list.append(instance)

        if instance.client.is_closed:
            instance.client = httpx.Client()

        return instance

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "GET")
    def get(self, url: str, query_params: Dict[str, Any] | None = None, headers: Dict[str, Any] | None = None, ) -> HTTPResponse:
        http_response: HTTPResponse = HTTPResponse(self.client.get(url, params=query_params, headers=headers, timeout=60))
        if not http_response.is_successful:
            SyncHTTPSession.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "PUT")
    def put(self, url: str, data: Dict[str, Any], headers: Dict[str, Any] | None = None) -> HTTPResponse:
        http_response: HTTPResponse = HTTPResponse(self.client.put(url, data=data, headers=headers, timeout=60))
        if not http_response.is_successful:
            SyncHTTPSession.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "POST")
    def post(self, url: str, data: Dict[str, Any] | None = None, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        data_string: str | None = None
        if data is not None:
            data_string = json.dumps(data)

            if headers is None:
                headers = {}
            headers["content-type"] = "application/json"

        http_response: HTTPResponse = HTTPResponse(self.client.post(url, data=data_string, headers=headers, timeout=60))  # type: ignore[arg-type]
        if not http_response.is_successful:
            SyncHTTPSession.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "DELETE")
    def delete(self, url: str, headers: Dict[str, Any] | None = None) -> HTTPResponse:
        http_response: HTTPResponse = HTTPResponse(self.client.delete(url, headers=headers, timeout=60))
        if not http_response.is_successful:
            SyncHTTPSession.raise_http_exception(http_response)

        return http_response


class HTTPModel(DataClass):

    @abstractmethod
    def __init__(self, **data: Any):
        super().__init__(**data)

    @staticmethod
    async def get_one(cls: type, url: str, query_params: Dict[str, Any] | None = None, http_session: AsyncHTTPSession | None = None) -> DataClass:
        if http_session is None:
            http_session = AsyncHTTPSession(url)

        if not issubclass(cls, BaseModel):
            raise ServerSideException(f"{cls.__name__} is not a Pydantic subclass")

        response: HTTPResponse = await http_session.get(url=url, query_params=query_params)
        return cls(**response.data)  # type: ignore[return-value]

    @staticmethod
    async def get_multiple(cls: type, url: str, query_params: Dict[str, Any] | None = None, headers: Dict[str, Any] | None = None, http_session: AsyncHTTPSession | None = None) -> List[DataClass]:
        if http_session is None:
            http_session = AsyncHTTPSession(url)

        if not issubclass(cls, BaseModel):
            raise ServerSideException(f"{cls.__name__} is not a Pydantic subclass")

        response: HTTPResponse = await http_session.get(url=url, query_params=query_params, headers=headers)
        return [cls(**data) for data in response.data]  # type: ignore[misc]

    @staticmethod
    async def post_return_one(cls: type, url: str, data: Dict[Any, Any] | None = None, headers: Dict[str, Any] | None = None, http_session: AsyncHTTPSession | None = None) -> DataClass:
        if http_session is None:
            http_session = AsyncHTTPSession(url)

        if not issubclass(cls, BaseModel):
            raise ServerSideException(f"{cls.__name__} is not a Pydantic subclass")

        response: HTTPResponse = await http_session.post(url=url, data=data, headers=headers)
        return cls(**response.data)  # type: ignore[return-value]
