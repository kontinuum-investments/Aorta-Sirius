import functools
from logging import Logger
from typing import Dict, Any, List, Callable

import beanie.odm.fields
from beanie import Document, init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from sirius import common, application_performance_monitoring
from sirius.application_performance_monitoring import Operation
from sirius.constants import EnvironmentVariable
from sirius.database.exceptions import DatabaseException, NonUniqueResultException, UncommittedRelationalDocumentException

client: AsyncIOMotorClient = None
database_name: str = common.get_environmental_variable(EnvironmentVariable.DATABASE_NAME)
logger: Logger = application_performance_monitoring.get_logger()


@application_performance_monitoring.transaction(Operation.DATABASE, f"Connect to the {database_name} Database")
async def initialize() -> None:
    global client, database_name
    if client is not None:
        return

    client = AsyncIOMotorClient(common.get_environmental_variable(EnvironmentVariable.MONGO_DB_CONNECTION_STRING))
    await init_beanie(database=client[database_name], document_models=DatabaseDocument.__subclasses__())


def transaction(transaction_name: str) -> Callable:
    def decorator(function: Callable) -> Callable:
        @application_performance_monitoring.transaction(Operation.AORTA_SIRIUS, transaction_name)
        @functools.wraps(function)
        async def wrapper(*args: List[Any], **kwargs: Dict[str, Any]) -> Any:
            await initialize()
            return await function(*args, **kwargs)

        return wrapper

    return decorator


class DatabaseDocument(Document):
    id: beanie.PydanticObjectId | None = None

    class Settings:
        validate_on_save = True
        use_state_management = True
        state_management_save_previous = True

        def __init__(self) -> None:
            pass

    def __init__(self, *args: List[Any], **kwargs: Dict[Any, Any]) -> None:
        for key, value in kwargs.items():
            if isinstance(value, DatabaseDocument):
                if value.id is None:
                    raise UncommittedRelationalDocumentException(f"Uncommitted document is trying to be related\nUncommitted Object: {str(object)}\nObject being related: {str(self)}")
                kwargs[key] = value.id  # type: ignore[assignment]

        super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]

    @application_performance_monitoring.transaction(Operation.DATABASE, "Save")
    async def commit(self) -> "DatabaseDocument":
        if self.id is None:
            return await super().save(link_rule=beanie.WriteRules.WRITE)
        else:
            return await super().save_changes()

    @application_performance_monitoring.transaction(Operation.DATABASE, "Delete")
    async def remove(self) -> None:
        return await super().delete()

    @classmethod
    @application_performance_monitoring.transaction(Operation.DATABASE, "Find Single")
    async def find_unique(cls, *args: List[Any], fetch_links: bool = False) -> "DatabaseDocument" | None:
        results_list: List[DatabaseDocument] = await super().find_many(*args).to_list()  # type: ignore[call-overload]

        if len(results_list) == 1:
            result: DatabaseDocument = results_list[0]
        elif len(results_list) == 0:
            return None
        else:
            raise NonUniqueResultException(f"Non-unique result found\nCollection: {cls.__name__}\nSearch Criteria: {str(*args)}")

        if fetch_links:
            await result.fetch_all_links()  # type: ignore[no-untyped-call]
        return result

    @classmethod
    @application_performance_monitoring.transaction(Operation.DATABASE, "Find Multiple")
    async def find_multiple(cls, search_criteria: Dict[Any, Any], fetch_links: bool = False) -> List["DatabaseDocument"]:
        results_list: List[DatabaseDocument] = await super().find_many(search_criteria).to_list()
        if fetch_links:
            for result in results_list:
                await result.fetch_all_links()  # type: ignore[no-untyped-call]
        return results_list

    @staticmethod
    @application_performance_monitoring.transaction(Operation.DATABASE, "Save All")
    async def commit_all(database_document_list: List["DatabaseDocument"]) -> List["DatabaseDocument"]:
        return [await database_document.commit() for database_document in database_document_list]
