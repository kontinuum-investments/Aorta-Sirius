import asyncio
from asyncio import AbstractEventLoop

import pytest


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    return asyncio.get_event_loop()

# async def clean_up_sandbox_environment() -> None:
#     wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
#     await wise_account.personal_profile._complete_all_transfers()
#     await wise_account.business_profile._complete_all_transfers()
#
#     for reserve_account in wise_account.personal_profile.reserve_account_list:
#         await reserve_account._set_balance(Decimal("0"))
#         await reserve_account.close()
