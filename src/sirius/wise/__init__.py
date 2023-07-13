import datetime
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
from sirius.wise.exceptions import CurrencyNotFoundException, ReserveAccountNotFoundException, OperationNotSupportedException, RecipientNotFoundException


class WiseAccountType(Enum):
    PRIMARY = auto()
    SECONDARY = auto()


class TransactionType(Enum):
    CARD: str = "CARD"
    CONVERSION: str = "CONVERSION"
    DEPOSIT: str = "DEPOSIT"
    TRANSFER: str = "TRANSFER"
    MONEY_ADDED: str = "MONEY_ADDED"


class WiseAccount(DataClass):
    type: WiseAccountType
    personal_profile: "PersonalProfile"
    business_profile: "BusinessProfile"
    _http_session: HTTPSession = PrivateAttr()

    @property
    def http_session(self) -> HTTPSession:
        return self._http_session

    async def initialize(self) -> None:
        profile_list: List[Profile] = await Profile.get_all(self)
        self.personal_profile = cast(PersonalProfile, next(filter(lambda p: p.type.lower() == "personal", profile_list)))
        self.business_profile = cast(BusinessProfile, next(filter(lambda p: p.type.lower() == "business", profile_list)))

    @staticmethod
    async def get(wise_account_type: WiseAccountType) -> "WiseAccount":
        environmental_variable: EnvironmentVariable

        if common.is_production_environment():
            environmental_variable = EnvironmentVariable.WISE_PRIMARY_ACCOUNT_API_KEY if wise_account_type == WiseAccountType.PRIMARY else EnvironmentVariable.WISE_SECONDARY_ACCOUNT_API_KEY
        else:
            environmental_variable = EnvironmentVariable.WISE_SANDBOX_ACCOUNT_API_KEY

        http_session: HTTPSession = HTTPSession(constants.URL, {"Authorization": f"Bearer {common.get_environmental_variable(environmental_variable)}"})

        wise_account: WiseAccount = WiseAccount.construct(type=wise_account_type)
        wise_account._http_session = http_session
        await wise_account.initialize()

        return wise_account


class Profile(DataClass):
    id: int
    type: str
    cash_account_list: List["CashAccount"] | None
    reserve_account_list: List["ReserveAccount"] | None
    recipient_list: List["Recipient"] | None
    debit_card_list: List["DebitCard"] | None
    wise_account: WiseAccount | None

    @property
    def http_session(self) -> HTTPSession:
        return self.wise_account.http_session

    async def get_cash_account(self, currency: Currency, is_create_if_unavailable: bool = False) -> "CashAccount":
        try:
            return next(filter(lambda c: c.currency == currency, self.cash_account_list))
        except StopIteration:
            if is_create_if_unavailable:
                return await CashAccount.open(self, currency)
            else:
                raise CurrencyNotFoundException(f"Currency not found: \n"
                                                f"Profile: {self.__class__.__name__}"
                                                f"Currency: {currency.value}")

    async def get_reserve_account(self, account_name: str, currency: Currency, is_create_if_unavailable: bool = False) -> "ReserveAccount":
        try:
            return next(filter(lambda r: r.name == account_name and r.currency == currency, self.reserve_account_list))
        except StopIteration:
            if is_create_if_unavailable:
                return await ReserveAccount.open(self, account_name, currency)
            else:
                raise ReserveAccountNotFoundException(f"Currency not found: \n"
                                                      f"Profile: {self.__class__.__name__}"
                                                      f"Reserve Account Name: {account_name}")

    def get_recipient(self, account_number: str) -> "Recipient":
        try:
            return next(filter(lambda r: r.account_number == account_number, self.recipient_list))
        except StopIteration:
            raise RecipientNotFoundException(f"Recipient not found: \n"
                                             f"Profile: {self.__class__.__name__}"
                                             f"Account Number: {account_number}")

    @staticmethod
    async def get_all(wise_account: WiseAccount) -> List["Profile"]:
        profile_list: List[Profile] = await HTTPModel.get_multiple(Profile, wise_account.http_session, constants.ENDPOINT__PROFILE__GET_ALL)  # type: ignore[assignment]

        for profile in profile_list:
            profile.wise_account = wise_account

        return [Profile(
            id=profile.id,
            type=profile.type,
            cash_account_list=await CashAccount.get_all(profile),
            reserve_account_list=await ReserveAccount.get_all(profile),
            recipient_list=await Recipient.get_all(profile),
            debit_card_list=[],
            # debit_card_list=await DebitCard.get_all(profile),
            wise_account=wise_account
        ) for profile in profile_list]


class PersonalProfile(Profile):
    pass


class BusinessProfile(Profile):
    pass


class Transaction(DataClass):
    account: "Account"
    date: datetime.datetime
    type: TransactionType
    description: str
    amount: Decimal


class Account(DataClass):
    id: int
    name: str | None
    currency: Currency
    balance: Decimal
    profile: Profile

    @property
    def http_session(self) -> HTTPSession:
        return self.profile.http_session

    async def close(self) -> None:
        if self.balance != Decimal("0"):
            raise OperationNotSupportedException(f"Cannot close account due to non-zero account balance:\n"
                                                 f"Account Name: {self.name}\n"
                                                 f"Currency: {self.currency.value}\n"
                                                 f"Balance: {str(self.balance)}")

        await self.http_session.delete(constants.ENDPOINT__BALANCE__CLOSE.replace("$profileId", str(self.profile.id)).replace("$balanceId", str(self.id)))
        await self.profile.wise_account.initialize()

    async def get_transactions(self, from_time: datetime.datetime | None = None, to_time: datetime.datetime | None = None) -> List["Transaction"]:
        if from_time is None:
            from_time = datetime.datetime.now() - datetime.timedelta(days=1)

        if to_time is None:
            to_time = datetime.datetime.now()

        response: HTTPResponse = await self.http_session.get(constants.ENDPOINT__BALANCE__GET_TRANSACTIONS.replace("$profileId", str(self.profile.id)).replace("$balanceId", str(self.id)), query_params={
            "currency": self.currency.value,
            "intervalStart": f"{from_time.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat().split('+')[0]}Z",
            "intervalEnd": f"{to_time.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat().split('+')[0]}Z",
            "type": "COMPACT"
        })

        return [Transaction(
            account=self,
            date=data["date"],
            type=TransactionType(data["details"]["type"]),
            description=data["details"]["description"],
            amount=Decimal(str(data["amount"]["value"])),
        ) for data in response.data["transactions"]]

    @staticmethod
    async def abstract_open(profile: Profile, account_name: str | None, currency: Currency, is_reserve_account: bool) -> "Account":
        data = {
            "currency": currency.value,
            "type": "SAVINGS" if is_reserve_account else "STANDARD"
        }

        if is_reserve_account:
            data["name"] = account_name

        response: HTTPResponse = await profile.http_session.post(constants.ENDPOINT__BALANCE__OPEN.replace("$profileId", str(profile.id)), data=data, headers={"X-idempotence-uuid": str(uuid.uuid4())})
        return Account(
            id=response.data["id"],
            name=account_name,
            currency=currency,
            balance=Decimal("0"),
            profile=profile
        )


class CashAccount(Account):

    async def transfer(self, to_account: Union["CashAccount", "ReserveAccount", "Recipient"], amount: Decimal, reference: str | None = None) -> "Transfer":
        if isinstance(to_account, ReserveAccount) and self.currency != to_account.currency:
            raise OperationNotSupportedException("Direct inter-currency transfers from a cash account to a reserve account is not supported")

        transfer: Transfer = Transfer.construct()
        if isinstance(to_account, CashAccount):
            transfer = await Transfer.intra_cash_account_transfer(self.profile, self, to_account, amount)
        elif isinstance(to_account, ReserveAccount):
            transfer = await Transfer.cash_to_savings_account_transfer(self.profile, self, to_account, amount)
        elif isinstance(to_account, Recipient):
            transfer = await Transfer.cash_to_third_party_cash_account_transfer(self.profile, self, to_account, amount, "" if reference is None else reference)

        await self.profile.wise_account.initialize()
        return transfer

    async def simulate_top_up(self, amount: Decimal) -> None:
        if not common.is_development_environment():
            raise OperationNotSupportedException("Simulations can only be done in a development environment")

        await self.profile.http_session.post(constants.ENDPOINT__SIMULATION__TOP_UP, {
            "profileId": self.profile.id,
            "balanceId": self.id,
            "currency": self.currency.value,
            "amount": float(amount)
        })

    @staticmethod
    async def get_all(profile: Profile) -> List["CashAccount"]:
        response: HTTPResponse = await profile.http_session.get(constants.ENDPOINT__ACCOUNT__GET_ALL__CASH_ACCOUNT.replace("$profileId", str(profile.id)))
        return [CashAccount(
            id=data["id"],
            name=data["name"],
            currency=Currency(data["cashAmount"]["currency"]),
            balance=Decimal(data["cashAmount"]["value"]),
            profile=profile
        ) for data in response.data]

    @staticmethod
    async def open(profile: Profile, currency: Currency) -> "CashAccount":
        return cast(CashAccount, await Account.abstract_open(profile, None, currency, False))


class ReserveAccount(Account):

    async def transfer(self, to_account: Union["CashAccount", "ReserveAccount", "Recipient"], amount: Decimal, reference: str | None = None) -> "Transfer":
        if self.currency != to_account.currency:
            raise OperationNotSupportedException("Direct inter-currency transfers from a reserve account is not supported")

        transfer: Transfer = await Transfer.savings_to_cash_account_transfer(self.profile, self, to_account, amount)  # type: ignore[arg-type]
        await self.profile.wise_account.initialize()
        return transfer

    @staticmethod
    async def get_all(profile: Profile) -> List["ReserveAccount"]:
        response: HTTPResponse = await profile.http_session.get(constants.ENDPOINT__ACCOUNT__GET_ALL__RESERVE_ACCOUNT.replace("$profileId", str(profile.id)))
        return [ReserveAccount(
            id=data["id"],
            name=data["name"],
            currency=Currency(data["cashAmount"]["currency"]),
            balance=Decimal(data["cashAmount"]["value"]),
            profile=profile,
        ) for data in response.data]

    @staticmethod
    async def open(profile: Profile, account_name: str, currency: Currency) -> "ReserveAccount":
        return cast(ReserveAccount, await Account.abstract_open(profile, account_name, currency, True))


class Recipient(DataClass):
    id: int
    account_holder_name: str
    currency: Currency
    is_self_owned: bool
    account_number: str
    _http_session: HTTPSession = PrivateAttr()

    @staticmethod
    async def get_all(profile: Profile) -> List["Recipient"]:
        response: HTTPResponse = await profile.http_session.get(constants.ENDPOINT__RECIPIENT__GET_ALL.replace("$profileId", str(profile.id)))
        raw_recipient_list: List[Dict[str, Any]] = list(filter(lambda d: d["details"]["accountNumber"] is not None, response.data))
        return [Recipient(
            id=data["id"],
            account_holder_name=data["accountHolderName"],
            currency=Currency(data["currency"]),
            is_self_owned=data["ownedByCustomer"],
            account_number=data["details"]["accountNumber"],
        ) for data in raw_recipient_list]


class Quote(DataClass):
    id: str
    from_currency: Currency
    to_currency: Currency
    from_amount: Decimal
    to_amount: Decimal
    exchange_rate: Decimal
    profile: Profile

    @staticmethod
    async def get_quote(profile: Profile, from_account: CashAccount | ReserveAccount, to_account: CashAccount | ReserveAccount | Recipient, amount: Decimal) -> "Quote":
        response: HTTPResponse = await profile.http_session.post(constants.ENDPOINT__QUOTE__GET.replace("$profileId", str(profile.id)), data={
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
            profile=profile
        )


class TransferType(Enum):
    CASH_TO_SAVINGS: int = auto()
    SAVINGS_TO_CASH: int = auto()
    CASH_TO_THIRD_PARTY: int = auto()
    SAVINGS_TO_THIRD_PARTY: int = auto()
    INTRA_CASH: int = auto()
    INTRA_SAVINGS: int = auto()


class Transfer(DataClass):
    id: int
    from_account: CashAccount | ReserveAccount
    to_account: CashAccount | ReserveAccount | Recipient
    from_amount: Decimal
    to_amount: Decimal
    reference: str | None
    transfer_type: TransferType

    @staticmethod
    async def intra_cash_account_transfer(profile: Profile, from_account: CashAccount, to_account: CashAccount, amount: Decimal) -> "Transfer":
        quote: Quote = await Quote.get_quote(profile, from_account, to_account, amount)
        response: HTTPResponse = await profile.http_session.post(constants.ENDPOINT__BALANCE__MOVE_MONEY_BETWEEN_BALANCES.replace("$profileId", str(profile.id)), data={"quoteId": quote.id},
                                                                 headers={"X-idempotence-uuid": str(uuid.uuid4())})
        return Transfer(
            id=response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(response.data["sourceAmount"]["value"])),
            to_account=to_account,
            to_amount=Decimal(str(response.data["targetAmount"]["value"])),
            reference=None,
            transfer_type=TransferType.INTRA_CASH,
        )

    @staticmethod
    async def cash_to_savings_account_transfer(profile: Profile, from_account: CashAccount, to_account: ReserveAccount, amount: Decimal) -> "Transfer":
        data = {
            "sourceBalanceId": from_account.id,
            "targetBalanceId": to_account.id
        }

        if from_account.currency != to_account.currency:
            quote: Quote = await Quote.get_quote(profile, from_account, to_account, amount)
            data["quoteId"] = cast(int, quote.id)
        else:
            data["amount"] = {  # type: ignore[assignment]
                "value": float(amount),
                "currency": to_account.currency.value
            }

        response: HTTPResponse = await profile.http_session.post(constants.ENDPOINT__BALANCE__MOVE_MONEY_BETWEEN_BALANCES.replace("$profileId", str(profile.id)), data=data, headers={"X-idempotence-uuid": str(uuid.uuid4())})

        return Transfer(
            id=response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(response.data["sourceAmount"]["value"])),
            to_account=to_account,
            to_amount=Decimal(str(response.data["targetAmount"]["value"])),
            reference=None,
            transfer_type=TransferType.CASH_TO_SAVINGS,
        )

    @staticmethod
    async def cash_to_third_party_cash_account_transfer(profile: Profile, from_account: CashAccount, to_account: Recipient, amount: Decimal, reference: str | None = None) -> "Transfer":
        quote: Quote = await Quote.get_quote(profile, from_account, to_account, amount)
        data: Dict[str, Any] = {
            "targetAccount": to_account.id,
            "quoteUuid": quote.id,
            "customerTransactionId": str(uuid.uuid4()),
            "details": {
                "reference": "" if reference is None else reference,
            }
        }

        create_transfer_response: HTTPResponse = await profile.http_session.post(constants.ENDPOINT__TRANSFER__CREATE_THIRD_PARTY_TRANSFER, data=data)
        await profile.http_session.post(constants.ENDPOINT__TRANSFER__FUND_THIRD_PARTY_TRANSFER.replace("$profileId", str(profile.id)).replace("$transferId", str(create_transfer_response.data["id"])),
                                        data={"type": "BALANCE"})

        return Transfer(
            id=create_transfer_response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(create_transfer_response.data["sourceValue"])),
            to_account=to_account,
            to_amount=Decimal(str(create_transfer_response.data["targetValue"])),
            reference=None,
            transfer_type=TransferType.CASH_TO_THIRD_PARTY,
        )

    @staticmethod
    async def savings_to_cash_account_transfer(profile: Profile, from_account: ReserveAccount, to_account: CashAccount, amount: Decimal) -> "Transfer":
        data = {
            "amount": {
                "value": float(amount),
                "currency": from_account.currency.value
            },
            "sourceBalanceId": from_account.id,
            "targetBalanceId": to_account.id,
        }

        response: HTTPResponse = await profile.http_session.post(constants.ENDPOINT__BALANCE__MOVE_MONEY_BETWEEN_BALANCES.replace("$profileId", str(profile.id)), data=data, headers={"X-idempotence-uuid": str(uuid.uuid4())})

        return Transfer(
            id=response.data["id"],
            from_account=from_account,
            from_amount=Decimal(str(response.data["sourceAmount"]["value"])),
            to_account=to_account,
            to_amount=Decimal(str(response.data["targetAmount"]["value"])),
            reference=None,
            transfer_type=TransferType.SAVINGS_TO_CASH,
        )


class DebitCard(DataClass):
    profile: Profile
    token: str
    expiry_date: datetime.datetime
    bank_identification_number: str

    # TODO: Find out why this endpoint returns a 403 (Unauthorized)
    @staticmethod
    async def get_all(profile: Profile) -> List["DebitCard"]:
        response: HTTPResponse = await profile.http_session.get(constants.ENDPOINT__DEBIT_CARD__GET_ALL.replace("$profileId", str(profile.id)))
        return [DebitCard(
            profile=profile,
            token=data["token"],
            expiry_date=datetime.datetime.fromisoformat(data["expiryDate"]),
            bank_identification_number=data["bankIdentificationNumber"]
        ) for data in response.data["cards"]]


WiseAccount.update_forward_refs()
Profile.update_forward_refs()
PersonalProfile.update_forward_refs()
BusinessProfile.update_forward_refs()
Account.update_forward_refs()
DebitCard.update_forward_refs()
Transaction.update_forward_refs()
