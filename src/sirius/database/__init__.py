import datetime
from typing import Union, cast, List, Dict, Any

import motor
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from sirius import common
from sirius.constants import EnvironmentVariable

client: AsyncIOMotorClient | None = None    # type: ignore[valid-type]
db: AsyncIOMotorDatabase | None = None    # type: ignore[valid-type]


async def initialize() -> None:
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(common.get_environmental_variable(EnvironmentVariable.MONGO_DB_CONNECTION_STRING),
                                                    uuidRepresentation="standard") if client is None else client
    db = client[common.get_environmental_variable(EnvironmentVariable.APPLICATION_NAME)] if db is None else db
    await init_beanie(db, document_models=DatabaseDocument.__subclasses__())


async def drop_collection(collection_name: str) -> None:
    await initialize()
    await cast(AsyncIOMotorDatabase, db).drop_collection(collection_name)    # type: ignore[attr-defined,valid-type]


class DatabaseDocument(Document):
    updated_timestamp: datetime.datetime | None = None
    created_timestamp: datetime.datetime = None

    async def save(self, *args: List[Any], **kwargs: Dict[str, Any]) -> None:
        current_timestamp: datetime.datetime = datetime.datetime.now()
        self.created_timestamp = current_timestamp if self.id is None else self.created_timestamp
        self.updated_timestamp = current_timestamp
        return await super().save()

    @classmethod
    async def get_by_id(cls, id_str: str) -> Union["DatabaseDocument", None]:
        await initialize()
        return await cls.get(id_str)
