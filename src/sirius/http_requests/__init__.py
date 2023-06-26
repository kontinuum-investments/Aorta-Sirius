import json
from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import httpx
from httpx import Response, Cookies, Headers, URL, AsyncClient
from pydantic import BaseModel

from sirius import application_performance_monitoring
from sirius.application_performance_monitoring import Operation
from sirius.http_requests.exceptions import ClientSideException, ServerSideException


@dataclass
class HTTPResponse:
    response: Response
    response_code: int
    is_successful: bool
    headers: Headers
    data: Optional[Dict[Any, Any]] = None
    response_text: Optional[str] = None
    cookies: Optional[Cookies] = None

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


class HTTPRequest:
    _instance_list: List["HTTPRequest"] = []
    client: AsyncClient
    host: str

    def __new__(cls, url_str: str) -> "HTTPRequest":
        host: str = URL(url_str).host
        instance: Optional[HTTPRequest] = next(filter(lambda h: h is not None and h.host == host, cls._instance_list), None)

        if instance is None:
            instance = super().__new__(cls)
            instance.host = host
            instance.client = httpx.AsyncClient()
            cls._instance_list.append(instance)

        if instance.client.is_closed:
            instance.client = httpx.AsyncClient()

        return instance

    def __init__(self, url_str: str) -> None:
        pass

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

    @staticmethod
    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "GET")
    async def get(url: str, query_params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        http_request: HTTPRequest = HTTPRequest(url)
        http_response: HTTPResponse = HTTPResponse(await http_request.client.get(url, params=query_params, headers=headers))
        if not http_response.is_successful:
            HTTPRequest.raise_http_exception(http_response)

        return http_response

    @staticmethod
    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "PUT")
    async def put(url: str, data: Dict[str, Any], headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        http_request: HTTPRequest = HTTPRequest(url)
        http_response: HTTPResponse = HTTPResponse(await http_request.client.put(url, data=data, headers=headers))
        if not http_response.is_successful:
            HTTPRequest.raise_http_exception(http_response)

        return http_response

    @staticmethod
    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "POST")
    async def post(url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        http_request: HTTPRequest = HTTPRequest(url)
        data_string: Optional[str] = None

        if headers is not None:
            headers["content-type"] = "application/json"

        if data is not None:
            data_string = json.dumps(data)

        http_response: HTTPResponse = HTTPResponse(await http_request.client.post(url, data=data_string, headers=headers))  # type: ignore[arg-type]
        if not http_response.is_successful:
            HTTPRequest.raise_http_exception(http_response)

        return http_response

    @staticmethod
    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "DELETE")
    async def delete(url: str, headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        http_request: HTTPRequest = HTTPRequest(url)
        http_response: HTTPResponse = HTTPResponse(await http_request.client.delete(url, headers=headers))
        if not http_response.is_successful:
            HTTPRequest.raise_http_exception(http_response)

        return http_response


class HTTPModel(BaseModel):
    _headers: Optional[Dict[str, Any]] = None

    @abstractmethod
    def __init__(self, **data: Any):
        super().__init__(**data)

    @classmethod
    async def get_one(cls, url: str, query_params: Optional[Dict[str, Any]] = None) -> "HTTPModel":
        response: HTTPResponse = await HTTPRequest.get(url=url, query_params=query_params, headers=cls._headers)
        return cls(**response.data)  # type: ignore[arg-type]

    @classmethod
    async def get_multiple(cls, url: str, query_params: Optional[Dict[str, Any]] = None) -> List["HTTPModel"]:
        response: HTTPResponse = await HTTPRequest.get(url=url, query_params=query_params, headers=cls._headers)
        return [cls(**data) for data in response.data]  # type: ignore[union-attr]

    @classmethod
    async def post_return_one(cls, url: str, data: Optional[Dict[Any, Any]] = None) -> "HTTPModel":
        response: HTTPResponse = await HTTPRequest.post(url=url, data=data, headers=cls._headers)
        return cls(**response.data)  # type: ignore[arg-type]
