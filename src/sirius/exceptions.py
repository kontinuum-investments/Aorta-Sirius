class SiriusException(Exception):
    pass


class ApplicationException(SiriusException):
    pass


class SDKClientException(SiriusException):
    pass
