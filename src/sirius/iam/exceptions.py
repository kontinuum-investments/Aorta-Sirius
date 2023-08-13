from sirius.exceptions import ApplicationException


class IAMException(ApplicationException):
    pass


class InvalidAccessTokenException(IAMException):
    pass


class AccessTokenRetrievalTimeoutException(IAMException):
    pass
