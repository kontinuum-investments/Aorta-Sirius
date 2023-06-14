from dataclasses import dataclass
from logging import Logger
from typing import List, Dict, Any, Optional

import bson
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

from sirius import common, application_performance_monitoring
from sirius.constants import EnvironmentVariable
from sirius.database.exceptions import DatabaseException, NonUniqueResultException

client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None
logger: Logger = application_performance_monitoring.get_logger()


def connect_to_database() -> None:
    global client, database
    if client is not None:
        return

    try:
        client = AsyncIOMotorClient(common.get_environmental_variable(EnvironmentVariable.MONGO_DB_CONNECTION_STRING))
        client.admin.command("ping")
        logger.debug("Successfully connected to the database")
    except Exception as e:
        raise DatabaseException("Unable to connect to the database", e)

    database = client[common.get_environmental_variable(EnvironmentVariable.DATABASE_NAME)]


@dataclass
class DatabaseDocument:
    _id: Optional[bson.ObjectId] = None

    @classmethod
    def get_collection(cls) -> AsyncIOMotorCollection:
        return database[cls.__name__]

    def get_dict(self, is_remove_id: bool = False) -> Dict[Any, Any]:
        return_dict: Dict[Any, Any] = self.__dict__

        if "collection" in return_dict.keys():
            return_dict.pop("collection")

        if is_remove_id or ("_id" in return_dict.keys() and return_dict.get("_id") is None):
            return_dict.pop("_id")

        return return_dict

    @classmethod
    def _get_database_document_from_dict(cls, data_dict: Dict[Any, Any], clazz: type) -> "DatabaseDocument":
        id_object: bson.ObjectId = data_dict.pop("_id")
        database_document = clazz(**data_dict)
        database_document._id = id_object
        return database_document

    async def save(self) -> "DatabaseDocument":
        if self._id is None:
            return await self.get_collection().insert_one(self.get_dict())
        else:
            return await self.get_collection().replace_one({"_id": self._id}, self.get_dict(is_remove_id=True))

    @classmethod
    async def save_many(cls, database_document_list: List["DatabaseDocument"]) -> List["DatabaseDocument"]:
        return [await database_document.save() for database_document in database_document_list]

    @classmethod
    async def find_one(cls, search_criteria: Dict[Any, Any]) -> Optional["DatabaseDocument"]:
        results_list: List[DatabaseDocument] = await cls.find_many(search_criteria)

        if len(results_list) == 0:
            return None
        elif len(results_list) == 1:
            return results_list[0]
        else:
            raise NonUniqueResultException(f"More than a single result found for a query expecting a single result:\nCollection:{cls.get_collection().name}\nSearch Criteria: {str(search_criteria)}")

    @classmethod
    async def find_many(cls, search_criteria: Dict[Any, Any]) -> List["DatabaseDocument"]:
        results_list: List[DatabaseDocument] = []
        collection: AsyncIOMotorCollection = cls.get_collection()

        for document in await collection.find(search_criteria).to_list(length=1000):
            results_list.append(cls._get_database_document_from_dict(document, cls))

        return results_list

    async def delete(self) -> None:
        collection: AsyncIOMotorCollection = self.get_collection()
        if self._id is None:
            raise DatabaseException(f"Unsaved data cannot be saved in the database: {str(self)}")

        await collection.delete_one({"_id": self._id})


connect_to_database()
