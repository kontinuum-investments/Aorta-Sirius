import asyncio
from asyncio import AbstractEventLoop

import pytest
import pytest_asyncio
from _decimal import Decimal

from sirius.wise import WiseAccount, WiseAccountType


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()


@pytest_asyncio.fixture(autouse=True, scope="session")
async def initialize_balances() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    for cash_account in wise_account.personal_profile.cash_account_list:
        if cash_account.balance > Decimal("1000"):
            continue

        await cash_account.simulate_top_up(Decimal("1000") - cash_account.balance)
