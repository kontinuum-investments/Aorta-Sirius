from enum import Enum


class EnvironmentVariable(Enum):
    ENVIRONMENT: str = "ENVIRONMENT"
    SENTRY_URL: str = "SENTRY_URL"
    MONGO_DB_CONNECTION_STRING: str = "MONGO_DB_CONNECTION_STRING"
    DATABASE_NAME: str = "DATABASE_NAME"
    DISCORD_BOT_TOKEN: str = "DISCORD_BOT_TOKEN"
    APPLICATION_NAME: str = "APPLICATION_NAME"
    WISE_PRIMARY_ACCOUNT_API_KEY: str = "WISE_PRIMARY_ACCOUNT_API_KEY"
    WISE_SECONDARY_ACCOUNT_API_KEY: str = "WISE_SECONDARY_ACCOUNT_API_KEY"
    ENTRA_ID_CLIENT_ID: str = "ENTRA_ID_CLIENT_ID"
    ENTRA_ID_TENANT_ID: str = "ENTRA_ID_TENANT_ID"
    TWILLO_AUTH_TOKEN: str = "TWILLO_AUTH_TOKEN"
    TWILLO_ACCOUNT_SID: str = "TWILLO_ACCOUNT_SID"
    TWILLO_WHATSAPP_NUMBER: str = "TWILLO_WHATSAPP_NUMBER"
