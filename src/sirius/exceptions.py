from typing import Dict, Any


class SiriusException(Exception):
    data: Dict[str, Any] = {}

    def __init__(self, message: str, data: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.data = data if data is not None else self.data


class ApplicationException(SiriusException):
    pass


class SDKClientException(SiriusException):
    pass


class OperationNotSupportedException(SDKClientException):
    pass
