import datetime
from enum import Enum
from typing import Union, cast, List, Dict, Any, Optional

import motor
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorGridFSBucket, AsyncIOMotorGridOutCursor
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from sirius import common
from sirius.common import DataClass
from sirius.constants import EnvironmentSecret
from sirius.database.exceptions import NonUniqueResultException, DocumentNotFoundException
from sirius.exceptions import SDKClientException

client: AsyncIOMotorClient | None = None  # type: ignore[valid-type]
db: AsyncIOMotorDatabase | None = None  # type: ignore[valid-type]
client_sync: MongoClient | None = None
db_sync: Database | None = None
fs: AsyncIOMotorGridFSBucket | None = None  # type: ignore[valid-type]
configuration_cache: Dict[str, Any] = {}


async def initialize() -> None:
    global client, db, fs
    client = motor.motor_asyncio.AsyncIOMotorClient(f"{common.get_environmental_secret(EnvironmentSecret.MONGO_DB_CONNECTION_STRING)}&retryWrites=false", uuidRepresentation="standard") if client is None else client
    db = client[common.get_environmental_secret(EnvironmentSecret.APPLICATION_NAME)] if db is None else db
    fs = AsyncIOMotorGridFSBucket(db)


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


class DatabaseFile(DataClass):
    id: ObjectId | None = None
    file_name: str
    metadata: Dict[str, Any]
    upload_date: datetime.datetime | None = None
    local_file_path: str | None = None

    @property
    def data(self) -> bytes:
        with open(self.local_file_path, "rb") as f:
            return f.read()

    def set_data(self, data: bytes) -> None:
        self.id = None
        self.upload_date = None
        self.local_file_path = common.get_new_temp_file_path()
        with open(self.local_file_path, "wb") as f:
            f.write(data)

    async def save(self) -> None:
        global fs

        await initialize()
        if self.local_file_path is None:
            raise SDKClientException("There is no file loaded to save")

        existing_database_file: DatabaseFile | None = await DatabaseFile.find(self.file_name)
        if existing_database_file is None:
            file_id = await fs.upload_from_stream(self.file_name, self.data, metadata=self.metadata)  # type: ignore[union-attr]
            self.id = file_id
        else:
            await existing_database_file.delete()
            await fs.upload_from_stream_with_id(existing_database_file.id, self.file_name, self.data, metadata=self.metadata)  # type: ignore[union-attr]

    async def delete(self) -> None:
        global fs

        await initialize()
        await fs.delete(self.id)  # type: ignore[union-attr]

    @staticmethod
    async def get(file_name: str) -> "DatabaseFile":
        global fs

        await initialize()
        file_path: str = common.get_new_temp_file_path()
        database_file: DatabaseFile = await DatabaseFile.get_minimal(file_name)
        stream = await fs.open_download_stream(database_file.id)  # type: ignore[union-attr]
        with open(file_path, "wb") as f:
            while True:
                chunk: bytes = await stream.readchunk()
                if not chunk:
                    break
                f.write(chunk)

        database_file.local_file_path = file_path
        return database_file

    @staticmethod
    async def get_minimal(file_name: str) -> "DatabaseFile":
        global fs

        await initialize()
        cursor: AsyncIOMotorGridOutCursor = fs.find({"filename": file_name})  # type: ignore[valid-type,union-attr]
        file_id_list: List[Dict[str, Any]] = await cursor.to_list(length=10)  # type: ignore[attr-defined]

        if len(file_id_list) == 1:
            file_data: Dict[str, Any] = file_id_list[0]
            return DatabaseFile(
                id=file_data["_id"],
                file_name=file_data["filename"],
                metadata=file_data["metadata"],
                upload_date=file_data["uploadDate"]
            )
        elif len(file_id_list) == 0:
            raise DocumentNotFoundException(f"No file named: {file_name}")
        else:
            raise NonUniqueResultException(f"More than one file with the file name: {file_name}")

    @staticmethod
    async def find(file_name: str) -> Optional["DatabaseFile"]:
        try:
            return await DatabaseFile.get_minimal(file_name)
        except DocumentNotFoundException:
            return None


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
            return [Configuration(type=configuration.type, key=configuration.key, value=configuration_cache[configuration.type][configuration.key])]

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
        if common.is_ci_cd_pipeline_environment() and self.name != "TEST_KEY":
            return self.default_value

        existing_configuration_list: List[Configuration] = cast(List[Configuration], Configuration.find_by_query_sync(Configuration.model_construct(type=self.__class__.__name__, key=self.name)))

        if len(existing_configuration_list) != 0:
            return existing_configuration_list[0].value
        else:
            Configuration(type=self.__class__.__name__, key=self.name, value=self.default_value).save_sync()
            # asyncio.ensure_future(Configuration(type=self.__class__.__name__, key=self.name, value=self.default_value).save())
            return self.default_value
