import json
from abc import abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

import httpx
from httpx import Response, Cookies, Headers
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

    def __init__(self) -> None:
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

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "GET")
    async def get(self, url: str, query_params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        async with httpx.AsyncClient() as client:
            http_response: HTTPResponse = HTTPResponse(await client.get(url, params=query_params, headers=headers))
            if not http_response.is_successful:
                HTTPRequest.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "PUT")
    async def put(self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        async with httpx.AsyncClient() as client:
            http_response: HTTPResponse = HTTPResponse(await client.put(url, data=data, headers=headers))
            if not http_response.is_successful:
                HTTPRequest.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "POST")
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        data_string: Optional[str] = None
        if headers is not None:
            headers["content-type"] = "application/json"

        if data is not None:
            data_string = json.dumps(data)

        async with httpx.AsyncClient() as client:
            http_response: HTTPResponse = HTTPResponse(await client.post(url, data=data_string, headers=headers))  # type: ignore[arg-type]
            if not http_response.is_successful:
                HTTPRequest.raise_http_exception(http_response)

        return http_response

    @application_performance_monitoring.transaction(Operation.HTTP_REQUEST, "DELETE")
    async def delete(self, url: str, headers: Optional[Dict[str, Any]] = None) -> HTTPResponse:
        async with httpx.AsyncClient() as client:
            http_response: HTTPResponse = HTTPResponse(await client.delete(url, headers=headers))
            if not http_response.is_successful:
                HTTPRequest.raise_http_exception(http_response)

        return http_response


class HTTPModel(BaseModel):
    _headers: Optional[Dict[str, Any]] = None

    @abstractmethod
    def __init__(self, **data: Any):
        super().__init__(**data)

    @classmethod
    async def get_one(cls, clazz: "HTTPModel", url: str, query_params: Optional[Dict[str, Any]] = None) -> "HTTPModel":
        response: HTTPResponse = await HTTPRequest().get(url=url, query_params=query_params, headers=clazz._headers)
        return clazz(**response.data)  # type: ignore[operator]

    @classmethod
    async def get_multiple(cls, clazz: "HTTPModel", url: str, query_params: Optional[Dict[str, Any]] = None) -> List["HTTPModel"]:
        response: HTTPResponse = await HTTPRequest().get(url=url, query_params=query_params, headers=clazz._headers)
        return [clazz(**data) for data in response.data]  # type: ignore[operator, union-attr]

    @classmethod
    async def post_return_one(cls, clazz: "HTTPModel", url: str, data: Optional[Dict[Any, Any]] = None) -> "HTTPModel":
        response: HTTPResponse = await HTTPRequest().post(url=url, data=data, headers=clazz._headers)
        return clazz(**response.data)  # type: ignore[operator]
