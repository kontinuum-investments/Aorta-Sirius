from typing import List, cast

import pytest

from sirius import database, common
from sirius.database import DatabaseDocument, DatabaseFile


class Test(DatabaseDocument):
    name: str


@pytest.mark.asyncio
async def test_crud_operations() -> None:
    # Create
    test = Test(name="John Doe")
    await test.save()

    # Read
    test = await Test.find_by_id(test.id)  # type: ignore[assignment]
    assert test is not None

    # Update
    test.name = "Jane Doe"
    await test.save()
    test = await Test.find_by_id(test.id)  # type: ignore[assignment]
    assert test.name == "Jane Doe"

    # Delete
    await test.delete()
    assert await Test.find_by_id(test.id) is None

    # Drop Collection
    await database.drop_collection(Test.__name__)


@pytest.mark.asyncio
async def test_find_by_query() -> None:
    await Test(name="John Doe").save()
    query_results: List[Test] = cast(List[Test], await Test.find_by_query(Test(name="John Doe")))
    assert len(query_results) != 0

    await database.drop_collection(Test.__name__)


def test_crud_operations_sync() -> None:
    # Create
    test = Test(name="John Doe")
    test.save_sync()

    # Read
    test = Test.find_by_id_sync(test.id)  # type: ignore[assignment]
    assert test is not None

    # Update
    test.name = "Jane Doe"
    test.save_sync()
    test = Test.find_by_id_sync(test.id)  # type: ignore[assignment]
    assert test.name == "Jane Doe"

    # Delete
    test.delete_sync()
    assert Test.find_by_id_sync(test.id) is None

    # Drop Collection
    database.drop_collection_sync(Test.__name__)


def test_find_by_query_sync() -> None:
    Test(name="John Doe").save_sync()
    query_results: List[Test] = cast(List[Test], Test.find_by_query_sync(Test(name="John Doe")))
    assert len(query_results) != 0

    database.drop_collection_sync(Test.__name__)


@pytest.mark.asyncio
async def test_crud_file_operations() -> None:
    data: bytes = common.get_unique_id().encode()
    file_name: str = "test_file"

    # Create
    database_file: DatabaseFile = DatabaseFile(file_name=file_name, metadata={"Hello": "World"}, purpose="Testing")
    database_file.load_data(data)
    await database_file.save()

    # Read
    saved_database_file: DatabaseFile = await DatabaseFile.get_minimal(file_name)
    assert saved_database_file.id == database_file.id

    # Update
    data = common.get_unique_id().encode()
    saved_database_file.load_data(data)
    await saved_database_file.save()
    updated_database_file: DatabaseFile = await DatabaseFile.get(file_name)
    assert updated_database_file.data == data

    # Delete
    await updated_database_file.delete()
    assert await DatabaseFile.find(file_name) is None
