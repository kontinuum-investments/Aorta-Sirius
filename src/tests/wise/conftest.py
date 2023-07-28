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
    await wise_account.personal_profile._populate_cash_accounts()
    await wise_account.personal_profile._populate_reserve_accounts()

    for cash_account in wise_account.personal_profile.cash_account_list:
        if cash_account.balance > Decimal("1000"):
            continue

        await cash_account.simulate_top_up(Decimal("1000") - cash_account.balance)

    test_reserve_account: ReserveAccount = await wise_account.personal_profile.get_reserve_account("Test", Currency.NZD)
    nzd_account: CashAccount = await wise_account.personal_profile.get_cash_account(Currency.NZD)
    await nzd_account.transfer(test_reserve_account, Decimal("100"))
