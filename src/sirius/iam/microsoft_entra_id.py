import base64
import base64
import datetime
from typing import Any, Dict
from urllib.parse import urlencode

import jwt
from aiocache import cached
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers, RSAPublicKey
from pydantic import BaseModel

from sirius import common
from sirius.constants import EnvironmentVariable
from sirius.http_requests import AsyncHTTPSession, HTTPResponse, ClientSideException
from sirius.iam.exceptions import InvalidAccessTokenException, AccessTokenRetrievalTimeoutException


class AuthenticationFlow(BaseModel):
    user_code: str
    device_code: str
    verification_uri: str
    message: str
    expiry_timestamp: datetime.datetime


class MicrosoftIdentityToken(BaseModel):
    access_token: str
    refresh_token: str
    id_token: str
    client_info: str
    name: str
    username: str
    entra_id_tenant_id: str
    application_id: str
    authenticated_timestamp: datetime.datetime
    inception_timestamp: datetime.datetime
    expiry_timestamp: datetime.datetime
    user_id: str
    subject_id: str
    scope: str | None = None


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
        entra_id_tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id

        jwks_location_url: str = f"https://login.microsoftonline.com/{entra_id_tenant_id}/.well-known/openid-configuration"
        jwks_location_response: HTTPResponse = await AsyncHTTPSession(jwks_location_url).get(jwks_location_url)
        jws_response: HTTPResponse = await AsyncHTTPSession(jwks_location_response.data["jwks_uri"]).get(jwks_location_response.data["jwks_uri"])
        return next(filter(lambda j: j["kid"] == key_id, jws_response.data["keys"]))

    @staticmethod
    async def _rsa_public_from_access_token(access_token: str, entra_id_tenant_id: str | None = None) -> RSAPublicKey:
        entra_id_tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        key_id: str = jwt.get_unverified_header(access_token)["kid"]
        jwk: Dict[str, Any] = await MicrosoftIdentity._get_microsoft_jwk(key_id, entra_id_tenant_id)

        return RSAPublicNumbers(
            n=int.from_bytes(base64.urlsafe_b64decode(jwk["n"].encode("utf-8") + b"=="), "big"),
            e=int.from_bytes(base64.urlsafe_b64decode(jwk["e"].encode("utf-8") + b"=="), "big")
        ).public_key(default_backend())

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

            entra_id_client_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
            entra_id_tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
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

        except AccessTokenRetrievalTimeoutException as e:
            raise e
        except Exception:
            raise InvalidAccessTokenException("Invalid token supplied")

    @staticmethod
    def get_login_url(redirect_url: str,
                      authentication_id: str | None = None,
                      entra_id_tenant_id: str | None = None,
                      entra_id_client_id: str | None = None,
                      scope: str | None = None) -> str:
        entra_id_tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        entra_id_client_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
        scope = "User.Read" if scope is None else scope
        authentication_id = common.get_unique_id() if authentication_id is None else authentication_id

        params: Dict[str, str] = {"client_id": entra_id_client_id,
                                  "response_type": "code",
                                  "redirect_uri": redirect_url,
                                  "response_mode": "query",
                                  "scope": scope,
                                  "state": authentication_id}

        return f"https://login.microsoftonline.com/{entra_id_tenant_id}/oauth2/v2.0/authorize?{urlencode(params)}"

    @staticmethod
    async def get_access_token(code: str, redirect_url: str, entra_id_tenant_id: str | None = None, entra_id_client_id: str | None = None) -> str:
        entra_id_tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if entra_id_tenant_id is None else entra_id_tenant_id
        entra_id_client_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_CLIENT_ID) if entra_id_client_id is None else entra_id_client_id
        url: str = f"https://login.microsoftonline.com/{entra_id_tenant_id}/oauth2/v2.0/token"

        try:
            response: HTTPResponse = await AsyncHTTPSession(url).post(url, data={"client_id": entra_id_client_id,
                                                                                 "redirect_uri": redirect_url,
                                                                                 "code": code,
                                                                                 "grant_type": "authorization_code"})
        except ClientSideException as e:
            response = e.data["http_response"]
            raise ClientSideException(response.data["error_description"])

        return response.data["access_token"]
