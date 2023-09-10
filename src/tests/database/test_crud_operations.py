from typing import cast

import pytest

from sirius import database
from sirius.database import DatabaseDocument, initialize, db


class Test(DatabaseDocument):
    name: str


@pytest.mark.asyncio
async def test_crud() -> None:
    await initialize()

    # Create
    test = Test(name="John Doe")
    await test.save()

    # Read
    test = await Test.get_by_id(test.id)    # type: ignore[assignment]
    assert test is not None

    # Update
    test.name = "Jane Doe"
    await test.save()
    test = await Test.get_by_id(test.id)    # type: ignore[assignment]
    assert test.name == "Jane Doe"

    # Delete
    await test.delete()
    assert await Test.get_by_id(test.id) is None

    # Drop Collection
    await database.drop_collection(Test.__name__)
