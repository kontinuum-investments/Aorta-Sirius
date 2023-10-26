import asyncio
from asyncio import AbstractEventLoop

import pytest


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()
