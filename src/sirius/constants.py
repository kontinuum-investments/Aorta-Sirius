from enum import Enum


class EnvironmentVariable(Enum):
    ENVIRONMENT: str = "ENVIRONMENT"
    SENTRY_URL: str = "SENTRY_URL"
    MONGO_DB_CONNECTION_STRING: str = "MONGODB_CONNECTION_STRING"
    DATABASE_NAME: str = "DATABASE_NAME"
