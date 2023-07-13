from sirius import common

URL: str = "https://api.transferwise.com" if common.is_production_environment() else "https://api.sandbox.transferwise.tech"
ENDPOINT__PROFILE__GET_ALL: str = f"{URL}/v2/profiles"
ENDPOINT__ACCOUNT__GET_ALL__CASH_ACCOUNT: str = f"{URL}/v4/profiles/$profileId/balances?types=STANDARD"
ENDPOINT__ACCOUNT__GET_ALL__RESERVE_ACCOUNT: str = f"{URL}/v4/profiles/$profileId/balances?types=SAVINGS"

ENDPOINT__BALANCE__MOVE_MONEY_BETWEEN_BALANCES: str = f"{URL}/v2/profiles/$profileId/balance-movements"
ENDPOINT__BALANCE__OPEN: str = f"{URL}/v3/profiles/$profileId/balances"
ENDPOINT__BALANCE__CLOSE: str = f"{URL}/v3/profiles/$profileId/balances/$balanceId"
ENDPOINT__TRANSFER__CREATE_THIRD_PARTY_TRANSFER: str = f"{URL}/v1/transfers"
ENDPOINT__TRANSFER__FUND_THIRD_PARTY_TRANSFER: str = f"{URL}/v3/profiles/$profileId/transfers/$transferId/payments"
ENDPOINT__DEBIT_CARD__GET_ALL: str = f"{URL}/v3/spend/profiles/$profileId/cards"

ENDPOINT__QUOTE__GET: str = f"{URL}/v3/profiles/$profileId/quotes"
ENDPOINT__INTRA_ACCOUNT_TRANSFER__CREATE: str = f"{URL}/v2/profiles/$profileId/balance-movements"
ENDPOINT__RECIPIENT__GET_ALL: str = f"{URL}/v1/accounts?profile=$profileId"
ENDPOINT__SIMULATION__TOP_UP: str = f"{URL}/v1/simulation/balance/topup"
