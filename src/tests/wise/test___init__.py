import pytest
from _decimal import Decimal

from sirius.common import Currency
from sirius.wise import WiseAccount, WiseAccountType, Transfer, CashAccount, ReserveAccount, Recipient, CurrencyNotFoundException, ReserveAccountNotFoundException, OperationNotSupportedException


@pytest.mark.asyncio
async def test_get_invalid_cash_account() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    with pytest.raises(CurrencyNotFoundException):
        wise_account.personal_profile.get_cash_account(Currency.LKR)


@pytest.mark.asyncio
async def test_get_invalid_reserve_account() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    with pytest.raises(ReserveAccountNotFoundException):
        wise_account.personal_profile.get_reserve_account("A")


@pytest.mark.asyncio
async def test_intra_cash_account_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    usd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.USD)
    gbp_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.GBP)
    transfer: Transfer = await usd_account.transfer(gbp_account, Decimal("1"))
    assert transfer.id is not None


@pytest.mark.asyncio
async def test_cash_to_same_currency_savings_account_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    nzd_account: CashAccount = wise_account.personal_profile.get_cash_account(Currency.NZD)
    reserve_account: ReserveAccount = next(filter(lambda a: a.currency == Currency.NZD, wise_account.personal_profile.reserve_account_list))
    transfer: Transfer = await nzd_account.transfer(reserve_account, Decimal("1"))
    assert transfer.id is not None


@pytest.mark.asyncio
async def test_cash_to_same_currency_third_party_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    usd_account: CashAccount = next(filter(lambda a: a.currency == Currency.USD, wise_account.personal_profile.cash_account_list))
    recipient: Recipient = next(filter(lambda a: a.currency == Currency.USD, wise_account.personal_profile.recipient_list))
    transfer: Transfer = await usd_account.transfer(recipient, Decimal("1"))
    assert transfer.id is not None


@pytest.mark.asyncio
async def test_cash_to_different_currency_third_party_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    nzd_account: CashAccount = next(filter(lambda a: a.currency == Currency.NZD, wise_account.personal_profile.cash_account_list))
    recipient: Recipient = next(filter(lambda a: a.currency == Currency.USD, wise_account.personal_profile.recipient_list))
    transfer: Transfer = await nzd_account.transfer(recipient, Decimal("1"))
    assert transfer.id is not None


@pytest.mark.asyncio
async def test_cash_to_different_currency_third_party_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    nzd_account: CashAccount = next(filter(lambda a: a.currency == Currency.NZD, wise_account.personal_profile.cash_account_list))
    recipient: Recipient = next(filter(lambda a: a.currency == Currency.USD, wise_account.personal_profile.recipient_list))
    transfer: Transfer = await nzd_account.transfer(recipient, Decimal("1"))
    assert transfer.id is not None


@pytest.mark.asyncio
async def test_savings_to_same_currency_cash_account_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    reserve_account: ReserveAccount = next(filter(lambda a: a.currency == Currency.NZD, wise_account.personal_profile.reserve_account_list))
    nzd_account: CashAccount = next(filter(lambda a: a.currency == Currency.NZD, wise_account.personal_profile.cash_account_list))
    transfer: Transfer = await reserve_account.transfer(nzd_account, Decimal("1"))
    assert transfer.id is not None


@pytest.mark.asyncio
async def test_savings_to_different_currency_cash_account_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    reserve_account: ReserveAccount = next(filter(lambda a: a.currency == Currency.NZD, wise_account.personal_profile.reserve_account_list))
    usd_account: CashAccount = next(filter(lambda a: a.currency == Currency.USD, wise_account.personal_profile.cash_account_list))

    with pytest.raises(OperationNotSupportedException):
        await reserve_account.transfer(usd_account, Decimal("1"))


@pytest.mark.asyncio
async def test_cash_account_to_different_currency_reserve_account_transfer() -> None:
    wise_account: WiseAccount = await WiseAccount.get(WiseAccountType.PRIMARY)
    reserve_account: ReserveAccount = next(filter(lambda a: a.currency == Currency.NZD, wise_account.personal_profile.reserve_account_list))
    usd_account: CashAccount = next(filter(lambda a: a.currency == Currency.USD, wise_account.personal_profile.cash_account_list))

    with pytest.raises(OperationNotSupportedException):
        await usd_account.transfer(reserve_account, Decimal("1"))
