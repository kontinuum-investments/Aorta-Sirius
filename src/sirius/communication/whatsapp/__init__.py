import asyncio

from greenletio import async_
from twilio.rest import Client
from twilio.rest.api.v2010.account.message import MessageInstance

from sirius import common
from sirius.communication.whatsapp import constants
from sirius.constants import EnvironmentVariable

twillo_client: Client | None = None


async def send_message(phone_number_string: str, message: str) -> MessageInstance:
    return await asyncio.get_event_loop().run_in_executor(None, _sync_send_message, phone_number_string, message)


def _sync_send_message(phone_number_string: str, message: str) -> MessageInstance:
    global twillo_client
    twillo_account_sid: str = common.get_environmental_variable(EnvironmentVariable.TWILLO_ACCOUNT_SID)
    twillo_auth_token: str = common.get_environmental_variable(EnvironmentVariable.TWILLO_AUTH_TOKEN)
    twillo_client = Client(twillo_account_sid, twillo_auth_token) if twillo_client is None else twillo_client

    return twillo_client.messages.create(from_=f"whatsapp:{common.get_environmental_variable(EnvironmentVariable.TWILLO_WHATSAPP_NUMBER)}",
                                         body=message,
                                         to=f"whatsapp:{phone_number_string}")
