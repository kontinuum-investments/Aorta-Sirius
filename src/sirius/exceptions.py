class SiriusException(Exception):

    def __init__(self, message: str) -> None:
        print(message)


class ApplicationException(SiriusException):
    pass
