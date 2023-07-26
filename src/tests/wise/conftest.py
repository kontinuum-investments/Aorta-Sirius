import asyncio
from asyncio import AbstractEventLoop

import pytest
import pytest_asyncio
from _decimal import Decimal

from sirius.common import Currency
from sirius.wise import WiseAccount, WiseAccountType, ReserveAccount, CashAccount


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()


@pytest_asyncio.fixture(autouse=True, scope="session")
async def initialize_balances() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    for cash_account in wise_account.personal_profile.cash_account_list:
        await cash_account._set_minimum_balance(Decimal("1000"))

    test_reserve_account: ReserveAccount = await wise_account.personal_profile.get_reserve_account("Test", Currency.NZD)
    await test_reserve_account._set_minimum_balance(Decimal("100"))
