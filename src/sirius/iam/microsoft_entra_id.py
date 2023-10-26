import asyncio
import base64
import datetime
import hashlib
import time
from typing import Any, Dict
from urllib.parse import urlencode

import jwt
from aiocache import cached
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers, RSAPublicKey
from fastapi import Request
from pydantic import BaseModel

from sirius import common
from sirius.communication.discord import AortaTextChannels, DiscordDefaults
from sirius.constants import EnvironmentSecret
from sirius.http_requests import AsyncHTTPSession, HTTPResponse, ClientSideException
from sirius.iam import constants
from sirius.iam.exceptions import InvalidAccessTokenException, AccessTokenRetrievalTimeoutException


class AuthenticationFlow(BaseModel):
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
    async def get_or_wait(cls, authentication_id: str) -> str:
        time_out_timestamp: int = int(time.time()) + constants.ACQUIRE_ACCESS_TOKEN__POLLING_TIMEOUT_SECONDS
        while int(time.time()) < time_out_timestamp:
            if authentication_id in cls.store:
                return cls.store.pop(authentication_id)

            await asyncio.sleep(constants.ACQUIRE_ACCESS_TOKEN__POLLING_SLEEP_SECONDS)

        raise AccessTokenRetrievalTimeoutException(f"Unauthenticated authentication: {authentication_id}")


class MicrosoftIdentity(BaseModel):
    audience_id: str
    authenticated_timestamp: datetime.datetime
    inception_timestamp: datetime.datetime
    expiry_timestamp: datetime.datetime
    application_id: str
    name: str
    scope: str
    user_id: str
    ip_address: str | None = None
    port_number: int | None = None

    @staticmethod
    @cached(ttl=86_400)
    async def _get_microsoft_jwk(key_id: str, entra_id_tenant_id: str | None = None) -> Dict[str, Any]:
        entra_id_tenant_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id

        jwks_location_url: str = f"https://login.microsoftonline.com/{entra_id_tenant_id}/.well-known/openid-configuration"
        jwks_location_response: HTTPResponse = await AsyncHTTPSession(jwks_location_url).get(jwks_location_url)
        jws_response: HTTPResponse = await AsyncHTTPSession(jwks_location_response.data["jwks_uri"]).get(jwks_location_response.data["jwks_uri"])
        return next(filter(lambda j: j["kid"] == key_id, jws_response.data["keys"]))

    @staticmethod
    async def _rsa_public_from_access_token(access_token: str, entra_id_tenant_id: str | None = None) -> RSAPublicKey:
        entra_id_tenant_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        key_id: str = jwt.get_unverified_header(access_token)["kid"]
        jwk: Dict[str, Any] = await MicrosoftIdentity._get_microsoft_jwk(key_id, entra_id_tenant_id)

        return RSAPublicNumbers(
            n=int.from_bytes(base64.urlsafe_b64decode(jwk["n"].encode("utf-8") + b"=="), "big"),
            e=int.from_bytes(base64.urlsafe_b64decode(jwk["e"].encode("utf-8") + b"=="), "big")
        ).public_key(default_backend())

    @staticmethod
    async def get_identity_from_request(request: Request, entra_id_client_id: str | None = None, entra_id_tenant_id: str | None = None) -> "MicrosoftIdentity":
        entra_id_client_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
        entra_id_tenant_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id

        if request.headers.get("authorization") is None or "Bearer " not in request.headers.get("authorization"):
            raise InvalidAccessTokenException("Invalid Token in Header")

        access_token = request.headers.get("authorization").replace("Bearer ", "")
        microsoft_identity: MicrosoftIdentity = await MicrosoftIdentity.get_identity_from_access_token(access_token, entra_id_client_id, entra_id_tenant_id)
        microsoft_identity.ip_address = request.client.host
        microsoft_identity.port_number = request.client.port

        return microsoft_identity

    @classmethod
    async def get_identity_from_access_token(cls, access_token: str, entra_id_client_id: str | None = None, entra_id_tenant_id: str | None = None) -> "MicrosoftIdentity":
        if common.is_development_environment():
            return MicrosoftIdentity(
                audience_id="",
                authenticated_timestamp=datetime.datetime.now(),
                inception_timestamp=datetime.datetime.now(),
                expiry_timestamp=datetime.datetime.now() + datetime.timedelta(hours=1),
                application_id=entra_id_client_id,
                name=f"Test Client",
                scope="",
                user_id="client@test.com"
            )

        try:

            entra_id_client_id = common.get_environmental_secret(
                EnvironmentSecret.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
            entra_id_tenant_id = common.get_environmental_secret(
                EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
            public_key: RSAPublicKey = await MicrosoftIdentity._rsa_public_from_access_token(access_token, entra_id_tenant_id)
            payload: Dict[str, Any] = jwt.decode(access_token, public_key, verify=True, audience=[entra_id_client_id], algorithms=["RS256"])

            return MicrosoftIdentity(
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
            raise InvalidAccessTokenException("Invalid token supplied")

    @staticmethod
    def get_login_url(redirect_url: str,
                      authentication_id: str,
                      entra_id_tenant_id: str | None = None,
                      entra_id_client_id: str | None = None,
                      scope: str | None = None) -> str:
        entra_id_tenant_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        entra_id_client_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
        scope = "User.Read" if scope is None else scope

        params: Dict[str, str] = {"client_id": entra_id_client_id,
                                  "response_type": "code",
                                  "redirect_uri": redirect_url,
                                  "response_mode": "query",
                                  "scope": scope,
                                  "state": authentication_id,
                                  "code_challenge_method": "S256",
                                  "code_challenge": base64.urlsafe_b64encode(hashlib.sha256(authentication_id.encode('utf-8')).digest()).decode('utf-8').replace("=", "")}

        return f"https://login.microsoftonline.com/{entra_id_tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"

    @staticmethod
    async def _get_access_token_from_authentication_code(authentication_code: str, authentication_id: str, redirect_url: str, entra_id_tenant_id: str | None = None, entra_id_client_id: str | None = None) -> str:
        entra_id_tenant_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        entra_id_client_id = common.get_environmental_secret(
            EnvironmentSecret.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
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

    @staticmethod
    async def get_access_token_remotely(redirect_url: str, discord_text_channel_name: str | None = None) -> str:
        authentication_id: str = common.get_unique_id()
        discord_text_channel_name = AortaTextChannels.NOTIFICATION.value if discord_text_channel_name is None else discord_text_channel_name

        await DiscordDefaults.send_message(discord_text_channel_name, "**Authentication Request**\n"
                                                                      f"*Sign-in here*: {MicrosoftIdentity.get_login_url(redirect_url, authentication_id)}")

        authentication_code: str = await MicrosoftEntraIDAuthenticationIDStore.get_or_wait(authentication_id)
        return await MicrosoftIdentity._get_access_token_from_authentication_code(authentication_code, authentication_id, redirect_url)
