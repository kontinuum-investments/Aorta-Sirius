import asyncio
import time
from asyncio import AbstractEventLoop

import pytest
import pytest_asyncio

from sirius.wise import WiseAccount, WiseAccountType


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()


@pytest_asyncio.fixture(autouse=True)
async def reset_wise_account() -> None:
    time.sleep(1)
    await WiseAccount.get(WiseAccountType.PRIMARY).personal_profile._reset()
