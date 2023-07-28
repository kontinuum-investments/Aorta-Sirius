from sirius.exceptions import SiriusException, SDKClientException


class WiseException(SiriusException):
    pass


class CashAccountNotFoundException(WiseException, SDKClientException):
    pass


class ReserveAccountNotFoundException(WiseException, SDKClientException):
    pass


class RecipientNotFoundException(WiseException, SDKClientException):
    pass
