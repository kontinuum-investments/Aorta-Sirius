import asyncio
from asyncio import AbstractEventLoop

import pytest
import pytest_asyncio

from sirius.database import initialize


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()


@pytest_asyncio.fixture(autouse=True)
async def initialize_database() -> None:
    await initialize()
