from sirius.exceptions import SiriusException


class DatabaseException(SiriusException):
    pass


class NonUniqueResultException(DatabaseException):
    pass
