import datetime
from enum import Enum
from typing import Union, cast, List, Dict, Any

import motor
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from sirius import common
from sirius.common import DataClass
from sirius.constants import EnvironmentSecret
from sirius.exceptions import SDKClientException

client: AsyncIOMotorClient | None = None  # type: ignore[valid-type]
db: AsyncIOMotorDatabase | None = None  # type: ignore[valid-type]
client_sync: MongoClient | None = None
db_sync: Database | None = None
configuration_cache: Dict[str, Any] = {}


async def initialize() -> None:
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(f"{common.get_environmental_secret(EnvironmentSecret.MONGO_DB_CONNECTION_STRING)}&retryWrites=false", uuidRepresentation="standard") if client is None else client
    db = client[common.get_environmental_secret(EnvironmentSecret.APPLICATION_NAME)] if db is None else db


def initialize_sync() -> None:
    global client_sync, db_sync
    client_sync = MongoClient(f"{common.get_environmental_secret(EnvironmentSecret.MONGO_DB_CONNECTION_STRING)}&retryWrites=false", uuidRepresentation="standard") if client_sync is None else client_sync
    db_sync = client_sync[common.get_environmental_secret(EnvironmentSecret.APPLICATION_NAME)] if db_sync is None else db_sync


async def drop_collection(collection_name: str) -> None:
    await initialize()
    await cast(AsyncIOMotorDatabase, db).drop_collection(collection_name)  # type: ignore[attr-defined,valid-type]


def drop_collection_sync(collection_name: str) -> None:
    initialize_sync()
    db_sync.drop_collection(collection_name)


class DatabaseDocument(DataClass):
    id: ObjectId | None = None
    updated_timestamp: datetime.datetime | None = None
    created_timestamp: datetime.datetime | None = None

    @classmethod
    async def _get_collection(cls) -> AsyncIOMotorCollection:  # type: ignore[valid-type]
        await initialize()
        global db
        return db[cls.__name__]  # type: ignore[index]

    @classmethod
    def _get_collection_sync(cls) -> Collection:
        initialize_sync()
        global db_sync
        return db_sync[cls.__name__]

    async def save(self) -> None:
        collection: AsyncIOMotorCollection = await self._get_collection()  # type: ignore[valid-type]

        if self.id is None:
            self.created_timestamp = datetime.datetime.now()
            object_id: ObjectId = (await collection.insert_one(self.model_dump(exclude={"id"}))).inserted_id  # type: ignore[attr-defined]
            self.__dict__.update(self.model_dump(exclude={"id"}))
            self.id = object_id
        else:
            self.updated_timestamp = datetime.datetime.now()
            await collection.replace_one({"_id": self.id}, self.model_dump(exclude={"id"}))  # type: ignore[attr-defined]

    def save_sync(self) -> None:
        collection: Collection = self._get_collection_sync()

        if self.id is None:
            self.created_timestamp = datetime.datetime.now()
            object_id: ObjectId = collection.insert_one(self.model_dump(exclude={"id"})).inserted_id
            self.__dict__.update(self.model_dump(exclude={"id"}))
            self.id = object_id
        else:
            self.updated_timestamp = datetime.datetime.now()
            collection.replace_one({"_id": self.id}, self.model_dump(exclude={"id"}))

    async def delete(self) -> None:
        collection: AsyncIOMotorCollection = await self._get_collection()  # type: ignore[valid-type]
        await collection.delete_one({'_id': self.id})  # type: ignore[attr-defined]

    def delete_sync(self) -> None:
        collection: Collection = self._get_collection_sync()
        collection.delete_one({'_id': self.id})

    @classmethod
    def get_model_by_raw_data(cls, raw_data: Dict[Any, Any]) -> "DatabaseDocument":
        object_id = raw_data.pop("_id")
        queried_object: DatabaseDocument = cls(**raw_data)
        queried_object.id = object_id
        return queried_object

    @classmethod
    async def find_by_id(cls, object_id: ObjectId) -> Union["DatabaseDocument", None]:
        collection: AsyncIOMotorCollection = await cls._get_collection()  # type: ignore[valid-type]
        object_model: Dict[str, Any] = await collection.find_one({'_id': object_id})  # type: ignore[attr-defined]
        return None if object_model is None else cls.get_model_by_raw_data(object_model)

    @classmethod
    def find_by_id_sync(cls, object_id: ObjectId) -> Union["DatabaseDocument", None]:
        collection: Collection = cls._get_collection_sync()
        object_model: Dict[str, Any] = collection.find_one({'_id': object_id})
        return None if object_model is None else cls.get_model_by_raw_data(object_model)

    @classmethod
    async def find_by_query(cls, database_document: "DatabaseDocument", query_limit: int = 100) -> List["DatabaseDocument"]:
        collection: AsyncIOMotorCollection = await cls._get_collection()  # type: ignore[valid-type]
        cursor = collection.find(database_document.model_dump(exclude={"id"}, exclude_none=True))  # type: ignore[attr-defined]
        return [cls.get_model_by_raw_data(document) for document in await cursor.to_list(length=query_limit)]

    @classmethod
    def find_by_query_sync(cls, database_document: "DatabaseDocument", query_limit: int = 100) -> List["DatabaseDocument"]:
        collection: Collection = cls._get_collection_sync()
        cursor = collection.find(database_document.model_dump(exclude={"id"}, exclude_none=True)).limit(query_limit)
        return [cls.get_model_by_raw_data(document) for document in cursor]


class Configuration(DatabaseDocument):
    type: str
    key: str
    value: str

    @classmethod
    def find_by_query_sync(cls, configuration: "Configuration", query_limit: int = 100) -> List["Configuration"]:  # type: ignore[override]
        global configuration_cache
        if configuration.type in configuration_cache and configuration.key in configuration_cache[configuration.type]:
            return configuration_cache[configuration.type][configuration.key]

        configuration_list: List[Configuration] = cast(List[Configuration], super().find_by_query_sync(configuration, query_limit))

        if len(configuration_list) > 1:
            raise SDKClientException(f"Duplicate configurations:\n"
                                     f"Type: {configuration.type}\n"
                                     f"Key: {configuration.key}")
        elif len(configuration_list) == 1:
            existing_configuration: Configuration = configuration_list[0]

            if existing_configuration.type in configuration_cache:
                configuration_cache[existing_configuration.type][existing_configuration.key] = existing_configuration.value
            else:
                configuration_cache[existing_configuration.type] = {existing_configuration.key: existing_configuration.value}

        return configuration_list


class ConfigurationEnum(Enum):
    default_value: Any

    def __init__(self, default_value: Any):
        self.default_value = default_value
        super().__init__()

    @property
    def value(self) -> Any:
        existing_configuration_list: List[Configuration] = cast(List[Configuration], Configuration.find_by_query_sync(Configuration.model_construct(type=self.__class__.__name__, key=self.name)))

        if len(existing_configuration_list) != 0:
            return existing_configuration_list[0].value
        else:
            Configuration(type=self.__class__.__name__, key=self.name, value=self.default_value).save_sync()
            # asyncio.ensure_future(Configuration(type=self.__class__.__name__, key=self.name, value=self.default_value).save())
            return self.default_value
