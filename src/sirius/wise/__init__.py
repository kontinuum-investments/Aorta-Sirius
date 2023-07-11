import uuid
from enum import Enum, auto
from typing import List, Dict, Any, Union, cast

from _decimal import Decimal
from pydantic import PrivateAttr

from sirius import common
from sirius.common import DataClass, Currency
from sirius.constants import EnvironmentVariable
from sirius.http_requests import HTTPSession, HTTPModel, HTTPResponse
from sirius.wise import constants
from sirius.wise.exceptions import CurrencyNotFoundException, ReserveAccountNotFoundException, OperationNotSupportedException


class WiseAccountType(Enum):
    PRIMARY = auto()
    SECONDARY = auto()


class WiseHTTPModel(DataClass):
    _http_session: HTTPSession = PrivateAttr()

    def __init__(self, **data: Any):
        super().__init__(**data)
        if "http_session" in data.keys():
            self._http_session = data.get("http_session")

    @property
    def http_session(self) -> HTTPSession:
        return self._http_session


class WiseAccount(WiseHTTPModel):
    personal_profile: "PersonalProfile"
    business_profile: "BusinessProfile"
    _http_session: HTTPSession = PrivateAttr()

    @staticmethod
    async def get(wise_account_type: WiseAccountType) -> "WiseAccount":
        environmental_variable: EnvironmentVariable

        if common.is_production_environment():
            environmental_variable = EnvironmentVariable.WISE_PRIMARY_ACCOUNT_API_KEY if wise_account_type == WiseAccountType.PRIMARY else EnvironmentVariable.WISE_SECONDARY_ACCOUNT_API_KEY
        else:
            environmental_variable = EnvironmentVariable.WISE_SANDBOX_ACCOUNT_API_KEY

        http_session: HTTPSession = HTTPSession(constants.URL, {"Authorization": f"Bearer {common.get_environmental_variable(environmental_variable)}"})
        profile_list: List[Profile] = await Profile.get_all(http_session)

        personal_profile: PersonalProfile = cast(PersonalProfile, next(filter(lambda p: p.type.lower() == "personal", profile_list)))
        business_profile: BusinessProfile = cast(BusinessProfile, next(filter(lambda p: p.type.lower() == "business", profile_list)))
        wise_account: WiseAccount = WiseAccount(personal_profile=personal_profile, business_profile=business_profile, http_session=http_session)

        return wise_account


class Profile(WiseHTTPModel):
    id: int
    type: str
    cash_account_list: List["CashAccount"] | None
    reserve_account_list: List["ReserveAccount"] | None
    recipient_list: List["Recipient"] | None
    _http_session: HTTPSession = PrivateAttr()

    def get_cash_account(self, currency: Currency) -> "CashAccount":
        try:
            return next(filter(lambda c: c.currency == currency, self.cash_account_list))
        except StopIteration:
            raise CurrencyNotFoundException(f"Currency not found: \n"
                                            f"Profile: {self.__class__.__name__}"
                                            f"Currency: {currency.value}")

    def get_reserve_account(self, account_name: str) -> "ReserveAccount":
        try:
            return next(filter(lambda r: r.name == account_name, self.reserve_account_list))
        except StopIteration:
            raise ReserveAccountNotFoundException(f"Currency not found: \n"
                                                  f"Profile: {self.__class__.__name__}"
                                                  f"Reserve Account Name: {account_name}")

    @staticmethod
    async def get_all(http_session: HTTPSession) -> List["Profile"]:
        profile_list: List[Profile] = await HTTPModel.get_multiple(Profile, http_session, constants.ENDPOINT__PROFILE__GET_ALL)  # type: ignore[return-value]

        return [Profile(
            http_session=http_session,
            id=profile.id,
            type=profile.type,
            cash_account_list=await CashAccount.get_all(http_session, profile),
            reserve_account_list=await ReserveAccount.get_all(http_session, profile),
            recipient_list=await Recipient.get_all(http_session, profile),
        ) for profile in profile_list]


class PersonalProfile(Profile):
    pass


class BusinessProfile(Profile):
    pass


class Account(WiseHTTPModel):
    id: int
    name: str | None
    currency: Currency
    balance: Decimal
    profile_id: int
    _http_session: HTTPSession = PrivateAttr()


class CashAccount(Account):
    _http_session: HTTPSession = PrivateAttr()

    @staticmethod
    async def get_all(http_session: HTTPSession, profile: Profile) -> List["CashAccount"]:
        response: HTTPResponse = await http_session.get(constants.ENDPOINT__ACCOUNT__GET_ALL__CASH_ACCOUNT.replace("$profileId", str(profile.id)))
        return [CashAccount(
            id=data["id"],
            name=data["name"],
            currency=Currency(data["cashAmount"]["currency"]),
            balance=Decimal(data["cashAmount"]["value"]),
            profile_id=profile.id,
            http_session=http_session
        ) for data in response.data]

    async def transfer(self, to_account: Union["CashAccount", "ReserveAccount", "Recipient"], amount: Decimal, reference: str | None = None) -> "Transfer":
        if isinstance(to_account, ReserveAccount) and self.currency != to_account.currency:
            raise OperationNotSupportedException("Direct inter-currency transfers from a cash account to a reserve account is not supported")

        if isinstance(to_account, CashAccount):
            return await Transfer.intra_cash_account_transfer(self.http_session, self.profile_id, self, to_account, amount)
        elif isinstance(to_account, ReserveAccount):
            return await Transfer.cash_to_savings_account_transfer(self.http_session, self.profile_id, self, to_account, amount)
        elif isinstance(to_account, Recipient):
            return await Transfer.cash_to_third_party_cash_account_transfer(self.http_session, self.profile_id, self, to_account, amount, "" if reference is None else reference)


class ReserveAccount(Account):
    _http_session: HTTPSession = PrivateAttr()

    @staticmethod
    async def get_all(http_session: HTTPSession, profile: Profile) -> List["ReserveAccount"]:
        response: HTTPResponse = await http_session.get(constants.ENDPOINT__ACCOUNT__GET_ALL__RESERVE_ACCOUNT.replace("$profileId", str(profile.id)))
        return [ReserveAccount(
            id=data["id"],
            name=data["name"],
            currency=Currency(data["cashAmount"]["currency"]),
            balance=Decimal(data["cashAmount"]["value"]),
            profile_id=profile.id,
            http_session=http_session
        ) for data in response.data]

    async def transfer(self, to_account: Union["CashAccount", "ReserveAccount", "Recipient"], amount: Decimal, reference: str | None = None) -> "Transfer":
        if self.currency != to_account.currency:
            raise OperationNotSupportedException("Direct inter-currency transfers from a reserve account is not supported")

        return await Transfer.savings_to_cash_account_transfer(self.http_session, self.profile_id, self, to_account, amount)


class Recipient(WiseHTTPModel):
    id: int
    account_holder_name: str
    currency: Currency
    is_self_owned: bool
    account_number: str
    _http_session: HTTPSession = PrivateAttr()

    @staticmethod
    async def get_all(http_session: HTTPSession, profile: Profile) -> List["Recipient"]:
        response: HTTPResponse = await http_session.get(constants.ENDPOINT__RECIPIENT__GET_ALL.replace("$profileId", str(profile.id)))
        raw_recipient_list: List[Dict[str, Any]] = list(filter(lambda d: d["details"]["accountNumber"] is not None, response.data))
        return [Recipient(
            id=data["id"],
            account_holder_name=data["accountHolderName"],
            currency=Currency(data["currency"]),
            is_self_owned=data["ownedByCustomer"],
            account_number=data["details"]["accountNumber"],
            http_session=http_session
        ) for data in raw_recipient_list]


class Quote(WiseHTTPModel):
    id: str
    from_currency: Currency
    to_currency: Currency
    from_amount: Decimal
    to_amount: Decimal
    exchange_rate: Decimal
    _http_session: HTTPSession = PrivateAttr()

    @staticmethod
    async def get_quote(http_session: HTTPSession, profile_id: int, from_account: CashAccount | ReserveAccount, to_account: CashAccount | ReserveAccount | Recipient, amount: Decimal) -> "Quote":
        response: HTTPResponse = await http_session.post(constants.ENDPOINT__QUOTE__GET.replace("$profileId", str(profile_id)), data={
            "sourceCurrency": from_account.currency.value,
            "targetCurrency": to_account.currency.value,
            "targetAmount": float(amount),
            "payOut": "BALANCE",
        })

        payment_option: Dict[str, Any] = next(filter(lambda p: p["payIn"] == "BALANCE", response.data["paymentOptions"]))
        return Quote(
            id=response.data["id"],
            from_currency=Currency(payment_option["sourceCurrency"]),
            to_currency=Currency(str(payment_option["targetCurrency"])),
            from_amount=Decimal(str(payment_option["sourceAmount"])),
            to_amount=Decimal(str(payment_option["targetAmount"])),
            exchange_rate=Decimal(str(response.data["rate"])),
            http_session=http_session
        )


class TransferType(Enum):
    CASH_TO_SAVINGS: int = auto()
    SAVINGS_TO_CASH: int = auto()
    CASH_TO_THIRD_PARTY: int = auto()
    SAVINGS_TO_THIRD_PARTY: int = auto()
    INTRA_CASH: int = auto()
    INTRA_SAVINGS: int = auto()


class Transfer(WiseHTTPModel):
    id: int
    from_account: CashAccount | ReserveAccount
    to_account: CashAccount | ReserveAccount | Recipient
    from_amount: Decimal
    to_amount: Decimal
    reference: str | None
    transfer_type: TransferType
    _http_session: HTTPSession = PrivateAttr()

    @staticmethod
    async def intra_cash_account_transfer(http_session: HTTPSession, profile_id: int, from_account: CashAccount, to_account: CashAccount, amount: Decimal) -> "Transfer":
        quote: Quote = await Quote.get_quote(http_session, profile_id, from_account, to_account, amount)
        response: HTTPResponse = await http_session.post(constants.ENDPOINT__BALANCE__MOVE_MONEY_BETWEEN_BALANCES.replace("$profileId", str(profile_id)), data={"quoteId": quote.id}, headers={"X-idempotence-uuid": str(uuid.uuid4())})
        return Transfer(
            id=response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(response.data["sourceAmount"]["value"])),
            to_account=to_account,
            to_amount=Decimal(str(response.data["targetAmount"]["value"])),
            reference=None,
            transfer_type=TransferType.INTRA_CASH,
            http_session=http_session
        )

    @staticmethod
    async def cash_to_savings_account_transfer(http_session: HTTPSession, profile_id: int, from_account: CashAccount, to_account: ReserveAccount, amount: Decimal) -> "Transfer":
        data = {
            "sourceBalanceId": from_account.id,
            "targetBalanceId": to_account.id
        }

        if from_account.currency != to_account.currency:
            quote: Quote = await Quote.get_quote(http_session, profile_id, from_account, to_account, amount)
            data["quoteId"] = quote.id
        else:
            data["amount"] = {
                "value": float(amount),
                "currency": to_account.currency.value
            }

        response: HTTPResponse = await http_session.post(constants.ENDPOINT__BALANCE__MOVE_MONEY_BETWEEN_BALANCES.replace("$profileId", str(profile_id)), data=data, headers={"X-idempotence-uuid": str(uuid.uuid4())})

        return Transfer(
            id=response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(response.data["sourceAmount"]["value"])),
            to_account=to_account,
            to_amount=Decimal(str(response.data["targetAmount"]["value"])),
            reference=None,
            transfer_type=TransferType.CASH_TO_SAVINGS,
            http_session=http_session
        )

    @staticmethod
    async def cash_to_third_party_cash_account_transfer(http_session: HTTPSession, profile_id: int, from_account: CashAccount, to_account: Recipient, amount: Decimal, reference: str | None = None) -> "Transfer":
        quote: Quote = await Quote.get_quote(http_session, profile_id, from_account, to_account, amount)
        data: Dict[str, Any] = {
            "targetAccount": to_account.id,
            "quoteUuid": quote.id,
            "customerTransactionId": str(uuid.uuid4()),
            "details": {
                "reference": "" if reference is None else reference,
            }
        }

        create_transfer_response: HTTPResponse = await http_session.post(constants.ENDPOINT__TRANSFER__CREATE_THIRD_PARTY_TRANSFER, data=data)
        await http_session.post(constants.ENDPOINT__TRANSFER__FUND_THIRD_PARTY_TRANSFER.replace("$profileId", str(profile_id)).replace("$transferId", str(create_transfer_response.data["id"])), data={"type": "BALANCE"})

        return Transfer(
            id=create_transfer_response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(create_transfer_response.data["sourceValue"])),
            to_account=to_account,
            to_amount=Decimal(str(create_transfer_response.data["targetValue"])),
            reference=None,
            transfer_type=TransferType.CASH_TO_THIRD_PARTY,
            http_session=http_session
        )

    @staticmethod
    async def savings_to_cash_account_transfer(http_session: HTTPSession, profile_id: int, from_account: ReserveAccount, to_account: CashAccount, amount: Decimal) -> "Transfer":
        data = {
            "amount": {
                "value": float(amount),
                "currency": from_account.currency.value
            },
            "sourceBalanceId": from_account.id,
            "targetBalanceId": to_account.id,
        }

        response: HTTPResponse = await http_session.post(constants.ENDPOINT__BALANCE__MOVE_MONEY_BETWEEN_BALANCES.replace("$profileId", str(profile_id)), data=data, headers={"X-idempotence-uuid": str(uuid.uuid4())})

        return Transfer(
            id=response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(response.data["sourceAmount"]["value"])),
            to_account=to_account,
            to_amount=Decimal(str(response.data["targetAmount"]["value"])),
            reference=None,
            transfer_type=TransferType.SAVINGS_TO_CASH,
            http_session=http_session
        )


WiseAccount.update_forward_refs()
Profile.update_forward_refs()
PersonalProfile.update_forward_refs()
BusinessProfile.update_forward_refs()
Account.update_forward_refs()
