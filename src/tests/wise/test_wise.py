# import datetime
# from _decimal import Decimal
# from typing import List
#
# import pytest
#
# from sirius.common import Currency
# from sirius.exceptions import OperationNotSupportedException
# from sirius.http_requests import ServerSideException
# from sirius.wise import WiseAccount, WiseAccountType, Transfer, CashAccount, ReserveAccount, Recipient, \
#     CashAccountNotFoundException, ReserveAccountNotFoundException, \
#     Transaction, RecipientNotFoundException, Quote
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_account_simulate_top_up() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#
#     starting_balance: Decimal = nzd_account.balance
#     top_up_amount: Decimal = Decimal("1")
#     nzd_account._simulate_top_up(top_up_amount)
#     assert nzd_account.balance == starting_balance + top_up_amount
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_reserve_account_simulate_top_up() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#     await nzd_account._set_balance(Decimal("0"))
#
#     starting_balance: Decimal = reserve_account.balance
#     top_up_amount: Decimal = Decimal("1")
#
#     await reserve_account._simulate_top_up(top_up_amount)
#     assert reserve_account.balance == starting_balance + top_up_amount
#     assert nzd_account.balance == Decimal("0")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_account_set_maximum_balance() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     nzd_account._simulate_top_up(Decimal("1001"))
#     await nzd_account._set_maximum_balance(Decimal("1000"))
#     assert nzd_account.balance == Decimal("1000")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_reserve_account_set_maximum_balance() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#
#     await nzd_account._set_balance(Decimal("0"))
#     await reserve_account._simulate_top_up(Decimal("1001"))
#     await reserve_account._set_maximum_balance(Decimal("1000"))
#
#     assert reserve_account.balance == Decimal("1000")
#     assert nzd_account.balance == Decimal("0")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_account_set_minimum_balance() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#
#     if nzd_account.balance > Decimal("1000"):
#         hkd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.HKD)
#         amount_to_transfer: Decimal = nzd_account.balance - Decimal("1000")
#         quote: Quote = Quote.get_quote(nzd_account.profile, nzd_account, hkd_account, amount_to_transfer, True)
#         await nzd_account.transfer(hkd_account, quote.to_amount)
#
#     nzd_account._set_minimum_balance(Decimal("1000"))
#     assert nzd_account.balance == Decimal("1000")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_reserve_account_set_minimum_balance() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#
#     if reserve_account.balance > Decimal("0"):
#         await reserve_account.transfer(nzd_account, reserve_account.balance)
#
#     await nzd_account._set_balance(Decimal("0"))
#     await reserve_account._set_minimum_balance(Decimal("1000"))
#     assert reserve_account.balance == Decimal("1000")
#     assert nzd_account.balance == Decimal("0")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_account_set_balance_from_low() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#
#     if nzd_account.balance > Decimal("1000"):
#         hkd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.HKD)
#         amount_to_transfer: Decimal = nzd_account.balance - Decimal("1000")
#         quote: Quote = Quote.get_quote(nzd_account.profile, nzd_account, hkd_account, amount_to_transfer, True)
#         await nzd_account.transfer(hkd_account, quote.to_amount)
#
#     await nzd_account._set_balance(Decimal("1000"))
#     assert nzd_account.balance == Decimal("1000")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_reserve_account_set_balance_from_low() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#
#     if reserve_account.balance > Decimal("0"):
#         nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#         await reserve_account.transfer(nzd_account, reserve_account.balance)
#
#     await reserve_account._set_balance(Decimal("1000"))
#     assert reserve_account.balance == Decimal("1000")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_account_set_balance_from_high() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     nzd_account._simulate_top_up(Decimal("1001"))
#     await nzd_account._set_balance(Decimal("1000"))
#     assert nzd_account.balance == Decimal("1000")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_reserve_account_set_balance_from_high() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#     await reserve_account._simulate_top_up(Decimal("1001"))
#     await reserve_account._set_balance(Decimal("1000"))
#     assert reserve_account.balance == Decimal("1000")
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_get_invalid_cash_account() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     with pytest.raises(CashAccountNotFoundException):
#         wise_account.personal_profile.get_cash_account(Currency.LKR)
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_get_invalid_reserve_account() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     with pytest.raises(ReserveAccountNotFoundException):
#         wise_account.personal_profile.get_reserve_account("A", Currency.NZD)
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_open_and_close_cash_account() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     cash_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.HUF, True)
#     cash_account.close()
#     with pytest.raises(CashAccountNotFoundException):
#         wise_account.personal_profile.get_cash_account(Currency.HUF)
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_close_account_with_non_zero_balance() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     cash_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD, True)
#     await cash_account._set_balance(Decimal("1"))
#
#     with pytest.raises(OperationNotSupportedException):
#         cash_account.close()
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_open_and_close_reserve_account() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.EUR, True)
#     reserve_account.close()
#     with pytest.raises(ReserveAccountNotFoundException):
#         wise_account.personal_profile.get_reserve_account("Test", Currency.EUR)
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_intra_cash_account_transfer() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     usd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.USD)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     usd_account._set_minimum_balance(Decimal("1"))
#     transfer: Transfer = await usd_account.transfer(nzd_account, Decimal("1"))
#     assert transfer.id is not None
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_to_same_currency_savings_account_transfer() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#     nzd_account._set_minimum_balance(Decimal("1"))
#     transfer: Transfer = await nzd_account.transfer(reserve_account, Decimal("1"))
#     assert transfer.id is not None
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_to_same_currency_third_party_transfer() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     usd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.USD)
#     recipient: Recipient = wise_account.personal_profile.get_recipient("12345678901234")
#     usd_account._set_minimum_balance(Decimal("5"))
#     transfer: Transfer = await usd_account.transfer(recipient, Decimal("1"))
#     assert transfer.id is not None
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_to_different_currency_third_party_transfer() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     recipient: Recipient = wise_account.personal_profile.get_recipient("12345678901234")
#     nzd_account._set_minimum_balance(Decimal("5"))
#     transfer: Transfer = await nzd_account.transfer(recipient, Decimal("1"))
#     assert transfer.id is not None
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_savings_to_same_currency_cash_account_transfer() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#     await reserve_account._set_minimum_balance(Decimal("5"))
#     transfer: Transfer = await reserve_account.transfer(nzd_account, Decimal("1"))
#     assert transfer.id is not None
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_savings_to_different_currency_cash_account_transfer() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#     usd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.USD)
#     with pytest.raises(OperationNotSupportedException):
#         await reserve_account.transfer(usd_account, Decimal("1"))
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_cash_account_to_different_currency_reserve_account_transfer() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     reserve_account: ReserveAccount = wise_account.personal_profile.get_reserve_account("Test", Currency.NZD, True)
#     usd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.USD)
#     with pytest.raises(OperationNotSupportedException):
#         await usd_account.transfer(reserve_account, Decimal("1"))
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_get_invalid_recipient() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     with pytest.raises(RecipientNotFoundException):
#         wise_account.personal_profile.get_recipient("A")
#
#
# @pytest.mark.skip(reason="Wise responds with a 404 HTTP error for some reason")
# @pytest.mark.asyncio
# async def test_get_debit_card() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     assert wise_account.personal_profile.debit_card_list[0].token is not None
#
#
# @pytest.mark.xfail(raises=ServerSideException)
# @pytest.mark.asyncio
# async def test_get_transactions() -> None:
#     wise_account: WiseAccount = WiseAccount.get(WiseAccountType.PRIMARY)
#     nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
#
#     try:
#         transactions_list: List[Transaction] = nzd_account.get_transactions(from_time=datetime.datetime.now() - datetime.timedelta(days=30))
#         assert transactions_list[0].amount is not None
#     except ServerSideException:
#         pass
