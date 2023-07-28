import asyncio
from asyncio import AbstractEventLoop

import pytest
import pytest_asyncio

from sirius.wise import WiseAccount, WiseAccountType


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()


@pytest_asyncio.fixture(autouse=True, scope="session")
async def complete_all_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    await wise_account.personal_profile._complete_all_transfers()
    await wise_account.business_profile._complete_all_transfers()
