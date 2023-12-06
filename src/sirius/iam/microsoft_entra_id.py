import asyncio
import base64
import datetime
import hashlib
import time
from typing import Any, Dict, Callable, Union
from urllib.parse import urlencode

import jwt

from sirius import common
from sirius.common import DataClass
from sirius.communication.discord import AortaTextChannels, DiscordDefaults
from sirius.constants import EnvironmentSecret
from sirius.http_requests import AsyncHTTPSession, HTTPResponse, ClientSideException
from sirius.iam import constants
from sirius.iam.exceptions import InvalidAccessTokenException, AccessTokenRetrievalTimeoutException


class AuthenticationFlow(DataClass):
    user_code: str
    device_code: str
    verification_uri: str
    message: str
    expiry_timestamp: datetime.datetime


class MicrosoftEntraIDAuthenticationIDStore:
    store: Dict[str, Any] = {}

    @classmethod
    def add(cls, authentication_id: str, authentication_code: str) -> None:
        cls.store[authentication_id] = authentication_code

    @classmethod
    async def _get_or_wait(cls, authentication_id: str) -> str:
        time_out_timestamp: int = int(time.time()) + constants.ACQUIRE_ACCESS_TOKEN__POLLING_TIMEOUT_SECONDS
        while int(time.time()) < time_out_timestamp:
            if authentication_id in cls.store:
                return cls.store.pop(authentication_id)

            await asyncio.sleep(constants.ACQUIRE_ACCESS_TOKEN__POLLING_SLEEP_SECONDS)

        raise AccessTokenRetrievalTimeoutException(f"Unauthenticated authentication: {authentication_id}")


class MicrosoftIdentity(DataClass):
    access_token: str
    audience_id: str
    authenticated_timestamp: datetime.datetime
    inception_timestamp: datetime.datetime
    expiry_timestamp: datetime.datetime
    application_id: str
    name: str
    scope: str
    user_id: str

    @classmethod
    def get_identity_from_access_token(cls, access_token: str) -> "MicrosoftIdentity":
        try:
            payload: Dict[str, Any] = jwt.decode(access_token, options={"verify_signature": False})
            return MicrosoftIdentity(
                access_token=access_token,
                audience_id=payload["aud"],
                authenticated_timestamp=datetime.datetime.utcfromtimestamp(payload["iat"]),
                inception_timestamp=datetime.datetime.utcfromtimestamp(payload["nbf"]),
                expiry_timestamp=datetime.datetime.utcfromtimestamp(payload["exp"]),
                application_id=payload["appid"],
                name=f"{payload['given_name']} {payload['family_name']}",
                scope=payload["scp"],
                user_id=payload["unique_name"]
            )

        except Exception:
            raise InvalidAccessTokenException("Invalid token")

    @staticmethod
    def get_login_url(redirect_url: str,
                      authentication_id: str,
                      entra_id_tenant_id: str | None = None,
                      entra_id_client_id: str | None = None,
                      scope: str | None = None,
                      url_shortener_function: Union[Callable, None] = None) -> str:

        entra_id_tenant_id = common.get_environmental_secret(EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        entra_id_client_id = common.get_environmental_secret(EnvironmentSecret.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
        scope = "User.Read" if scope is None else scope

        params: Dict[str, str] = {"client_id": entra_id_client_id,
                                  "response_type": "code",
                                  "redirect_uri": redirect_url,
                                  "response_mode": "query",
                                  "scope": scope,
                                  "state": authentication_id,
                                  "code_challenge_method": "S256",
                                  "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(authentication_id.encode('utf-8')).digest()).decode('utf-8').replace("=", "")}
        url: str = f"https://login.microsoftonline.com/{entra_id_tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"

        return url if url_shortener_function is None else url_shortener_function(url)

    @staticmethod
    async def get_access_token_remotely(redirect_url: str, discord_text_channel_name: str | None = None, url_shortener_function: Union[Callable, None] = None) -> str:
        authentication_id: str = common.get_unique_id()
        discord_text_channel_name = AortaTextChannels.NOTIFICATION.value if discord_text_channel_name is None else discord_text_channel_name
        sign_in_url: str = MicrosoftIdentity.get_login_url(redirect_url, authentication_id) if url_shortener_function is None else url_shortener_function(MicrosoftIdentity.get_login_url(redirect_url, authentication_id))

        await DiscordDefaults.send_message(discord_text_channel_name, "**Authentication Request**\n"
                                                                      f"*Sign-in here*: {sign_in_url}")

        authentication_code: str = await MicrosoftEntraIDAuthenticationIDStore._get_or_wait(authentication_id)
        return await MicrosoftIdentity._get_access_token_from_authentication_code(authentication_code, authentication_id, redirect_url)

    @staticmethod
    async def _get_access_token_from_authentication_code(authentication_code: str, authentication_id: str, redirect_url: str, entra_id_tenant_id: str | None = None, entra_id_client_id: str | None = None) -> str:
        entra_id_tenant_id = common.get_environmental_secret(EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        entra_id_client_id = common.get_environmental_secret(EnvironmentSecret.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
        url: str = f"https://login.microsoftonline.com/{entra_id_tenant_id}/oauth2/v2.0/token"

        try:
            response: HTTPResponse = await AsyncHTTPSession(url).post(url, data={"client_id": entra_id_client_id,
                                                                                 "redirect_uri": redirect_url,
                                                                                 "code": authentication_code,
                                                                                 "grant_type": "authorization_code",
                                                                                 "code_verifier": authentication_id}, is_form_url_encoded=True)
            return response.data["access_token"]
        except ClientSideException as e:
            response = e.data["http_response"]
            raise ClientSideException(response.data["error_description"])
