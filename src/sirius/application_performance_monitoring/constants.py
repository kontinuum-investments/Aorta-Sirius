from enum import Enum


class Operation(Enum):
    DATABASE: str = "Database"
    DISCORD: str = "Discord"
    HTTP_REQUEST: str = "HTTP Request"
    AORTA_SIRIUS: str = "Aorta-Sirius"
