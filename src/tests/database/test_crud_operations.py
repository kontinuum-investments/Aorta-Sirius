from typing import List, cast

import pytest

from sirius import database
from sirius.database import DatabaseDocument


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
