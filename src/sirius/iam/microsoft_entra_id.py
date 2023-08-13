import base64
import datetime
import json
from functools import cache
from typing import Any, Dict, List

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers, RSAPublicKey
from msal import PublicClientApplication
from pydantic import BaseModel

from sirius import common
from sirius.communication.discord import TextChannel
from sirius.constants import EnvironmentVariable
from sirius.exceptions import ApplicationException
from sirius.http_requests import AsyncHTTPSession, HTTPResponse
from sirius.iam.exceptions import InvalidAccessTokenException


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
    tenant_id: str
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
    ip_address: str
    scope: str
    user_id: str

    @staticmethod
    def _get_flow(public_client_application: PublicClientApplication, scopes: List[str]) -> tuple[dict[str, Any], AuthenticationFlow]:
        flow: Dict[str, Any] = public_client_application.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            raise ApplicationException("Fail to create device flow. Err: %s" % json.dumps(flow, indent=4))

        return flow, AuthenticationFlow(
            user_code=flow["user_code"],
            device_code=flow["device_code"],
            verification_uri=flow["verification_uri"],
            message=flow["message"],
            expiry_timestamp=datetime.datetime.utcfromtimestamp(flow["expires_at"]),
        )

    @staticmethod
    async def get_token(scopes: List[str], notification_text_channel: TextChannel, application_name: str, client_id: str | None = None, tenant_id: str | None = None) -> "MicrosoftIdentityToken":
        client_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_CLIENT_ID) if client_id is None else client_id
        tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if tenant_id is None else tenant_id
        public_client_application: PublicClientApplication = PublicClientApplication(client_id, authority=f"https://login.microsoftonline.com/{tenant_id}")

        flow: Dict[str, Any]
        authentication_flow: AuthenticationFlow
        flow, authentication_flow = MicrosoftIdentity._get_flow(public_client_application, scopes)

        await notification_text_channel.send_message(f"**Authentication Request**:\n"
                                                     f"Application Name: *{application_name}*\n"
                                                     f"User Code: *{authentication_flow.user_code}*\n"
                                                     f"Verification URI: *{authentication_flow.verification_uri}*\n"
                                                     f"Message: *{authentication_flow.message}*\n")

        identity_token_dict: Dict[str, Any] = public_client_application.acquire_token_by_device_flow(flow)
        return MicrosoftIdentityToken(
            scope=identity_token_dict["scope"],
            access_token=identity_token_dict["access_token"],
            refresh_token=identity_token_dict["refresh_token"],
            id_token=identity_token_dict["id_token"],
            client_info=identity_token_dict["client_info"],
            name=identity_token_dict["id_token_claims"]["name"],
            username=identity_token_dict["id_token_claims"]["preferred_username"],
            tenant_id=identity_token_dict["id_token_claims"]["tid"],
            application_id=identity_token_dict["id_token_claims"]["aud"],
            authenticated_timestamp=datetime.datetime.utcfromtimestamp(identity_token_dict["id_token_claims"]["iat"]),
            inception_timestamp=datetime.datetime.utcfromtimestamp(identity_token_dict["id_token_claims"]["nbf"]),
            expiry_timestamp=datetime.datetime.utcfromtimestamp(identity_token_dict["id_token_claims"]["exp"]),
            user_id=identity_token_dict["id_token_claims"]["oid"],
            subject_id=identity_token_dict["id_token_claims"]["sub"],
        )

    @staticmethod
    @cache
    async def _get_microsoft_jwk(key_id: str, tenant_id: str | None = None) -> Dict[str, Any]:
        tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if tenant_id is None else tenant_id

        jwks_location_url: str = f"https://login.microsoftonline.com/{tenant_id}/.well-known/openid-configuration"
        jwks_location_response: HTTPResponse = await AsyncHTTPSession(jwks_location_url).get(jwks_location_url)
        jws_response: HTTPResponse = await AsyncHTTPSession(jwks_location_response.data["jwks_uri"]).get(jwks_location_response.data["jwks_uri"])
        return next(filter(lambda j: j["kid"] == key_id, jws_response.data["keys"]))

    @staticmethod
    async def _rsa_public_from_access_token(access_token: str, tenant_id: str | None = None) -> RSAPublicKey:
        tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if tenant_id is None else tenant_id
        key_id: str = jwt.get_unverified_header(access_token)["kid"]
        jwk: Dict[str, Any] = await MicrosoftIdentity._get_microsoft_jwk(key_id, tenant_id)

        return RSAPublicNumbers(
            n=int.from_bytes(base64.urlsafe_b64decode(jwk["n"].encode("utf-8") + b"=="), "big"),
            e=int.from_bytes(base64.urlsafe_b64decode(jwk["e"].encode("utf-8") + b"=="), "big")
        ).public_key(default_backend())

    @classmethod
    async def get_identity_from_access_token(cls, access_token: str, client_id: str | None = None, tenant_id: str | None = None) -> "MicrosoftIdentity":
        client_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_CLIENT_ID) if client_id is None else client_id
        tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if tenant_id is None else tenant_id
        public_key: RSAPublicKey = await MicrosoftIdentity._rsa_public_from_access_token(access_token, tenant_id)

        try:
            payload: Dict[str, Any] = jwt.decode(access_token, public_key, verify=False, audience=[client_id], algorithms=["RS256"])
            return MicrosoftIdentity(
                audience_id=payload["aud"],
                authenticated_timestamp=datetime.datetime.utcfromtimestamp(payload["iat"]),
                inception_timestamp=datetime.datetime.utcfromtimestamp(payload["nbf"]),
                expiry_timestamp=datetime.datetime.utcfromtimestamp(payload["exp"]),
                application_id=payload["appid"],
                name=f"{payload['given_name']} {payload['family_name']}",
                ip_address=payload["ipaddr"],
                scope=payload["scp"],
                user_id=payload["unique_name"]
            )
        except Exception:
            raise InvalidAccessTokenException("Invalid token supplied")
