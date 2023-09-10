import datetime
from typing import Union, cast, List, Dict, Any

import motor
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from sirius import common
from sirius.common import DataClass
from sirius.constants import EnvironmentVariable

client: AsyncIOMotorClient | None = None  # type: ignore[valid-type]
db: AsyncIOMotorDatabase | None = None  # type: ignore[valid-type]


async def initialize() -> None:
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(common.get_environmental_variable(EnvironmentVariable.MONGO_DB_CONNECTION_STRING),
                                                    uuidRepresentation="standard") if client is None else client
    db = client[common.get_environmental_variable(EnvironmentVariable.APPLICATION_NAME)] if db is None else db


async def drop_collection(collection_name: str) -> None:
    await initialize()
    await cast(AsyncIOMotorDatabase, db).drop_collection(collection_name)  # type: ignore[attr-defined,valid-type]


class DatabaseDocument(DataClass):
    id: ObjectId | None = None
    updated_timestamp: datetime.datetime | None = None
    created_timestamp: datetime.datetime | None = None

    async def save(self) -> None:
        global db
        collection: AsyncIOMotorCollection = db[self.__class__.__name__]  # type: ignore[valid-type,index]

        if self.id is None:
            self.updated_timestamp = datetime.datetime.now()
            object_id: ObjectId = (await collection.insert_one(self.model_dump(exclude={"id"}))).inserted_id  # type: ignore[attr-defined]
            self._update_model(object_id, self.model_dump(exclude={"id"}))
        else:
            self.created_timestamp = datetime.datetime.now()
            await collection.replace_one({"_id": self.id}, self.model_dump(exclude={"id"}))  # type: ignore[attr-defined]

    async def delete(self) -> None:
        await initialize()
        collection: AsyncIOMotorCollection = db[self.__class__.__name__]  # type: ignore[valid-type,index]
        await collection.delete_one({'_id': self.id})  # type: ignore[attr-defined]

    def _update_model(self, object_id: ObjectId, new_model: Dict[str, Any]) -> None:
        self.__dict__.update(new_model)
        self.id = object_id

    @classmethod
    async def get_by_id(cls, object_id: ObjectId) -> Union["DatabaseDocument", None]:
        await initialize()
        collection: AsyncIOMotorCollection = db[cls.__name__]  # type: ignore[index,valid-type]
        object_model: Dict[str, Any] = await collection.find_one({'_id': object_id})  # type: ignore[attr-defined]

        if object_model is None:
            return None

        object_id = object_model.pop("_id")
        queried_object: DatabaseDocument = cls(**object_model)
        queried_object.id = object_id
        return queried_object
