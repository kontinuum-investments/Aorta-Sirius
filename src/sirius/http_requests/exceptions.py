from sirius.exceptions import ApplicationException


class HTTPException(ApplicationException):
    pass


class ClientSideException(HTTPException):
    pass


class ServerSideException(HTTPException):
    pass
