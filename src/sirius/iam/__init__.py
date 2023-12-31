import datetime
import json
from typing import Dict, Any, cast, Union, Callable

import jwt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from fastapi import Request
from jwt import InvalidTokenError, ExpiredSignatureError

from sirius.azure.key_vault import AzureKeyVault
from sirius.common import DataClass
from sirius.exceptions import SDKClientException
from sirius.iam import constants
from sirius.iam.exceptions import InvalidAccessTokenException
from sirius.iam.microsoft_entra_id import MicrosoftIdentity


class Identity(DataClass):
    microsoft_identity: MicrosoftIdentity
    ip_address: str | None = None
    port_number: int | None = None

    @staticmethod
    def get_private_key() -> RSAPrivateKey:
        try:
            private_key_string: str = AzureKeyVault.get(constants.AUTHENTICATION_KEY_NAME)
            return cast(RSAPrivateKey, serialization.load_pem_private_key(private_key_string.encode("utf-8"), None, backend=default_backend()))
        except SDKClientException:
            private_key: RSAPrivateKey = rsa.generate_private_key(public_exponent=65537, key_size=4096, backend=default_backend())
            AzureKeyVault.set(constants.AUTHENTICATION_KEY_NAME, private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ).decode("utf-8"))

            return private_key

    @staticmethod
    async def get_access_token_remotely(redirect_url: str,
                                        client_ip_address: str | None = None,
                                        client_port_number: int | None = None,
                                        url_shortener_function: Union[Callable, None] = None) -> str:

        microsoft_access_token: str = await MicrosoftIdentity.get_access_token_remotely(redirect_url, url_shortener_function=url_shortener_function)
        microsoft_identity: MicrosoftIdentity = MicrosoftIdentity.get_identity_from_access_token(microsoft_access_token)
        identity: Identity = Identity._get_identity_from_microsoft_identity(microsoft_identity, client_ip_address, client_port_number)
        return Identity.get_access_token_from_identity(identity)

    @staticmethod
    def get_identity_from_request(request: Request) -> "Identity":
        if (("Authorization" not in request.headers or "Bearer " not in request.headers.get("Authorization")) and
                ("access_token" not in request.cookies or "Bearer " not in request.cookies["access_token"])):
            raise InvalidAccessTokenException("Invalid Token")

        access_token: str = (request.headers.get("Authorization") if "Authorization" in request.headers else request.cookies.get("Authorization")).replace("Bearer ", "")
        return Identity.get_identity_from_access_token(access_token)

    @staticmethod
    def get_identity_from_access_token(access_token: str) -> "Identity":
        Identity._validate_jwt_token(access_token)
        payload: Dict[str, Any] = jwt.decode(access_token, options={"verify_signature": False})

        return Identity(**payload)

    @staticmethod
    def get_access_token_from_identity(identity: "Identity") -> str:
        payload: Dict[str, Any] = json.loads(identity.model_dump_json())
        payload["exp"] = datetime.datetime.utcnow() + datetime.timedelta(seconds=constants.DEFAULT_ACCESS_TOKEN_VALIDITY_SECONDS)

        return jwt.encode(payload, Identity.get_private_key(), algorithm="RS256")

    @staticmethod
    def _validate_jwt_token(jwt_token: str) -> None:
        try:
            jwt.decode(jwt_token, Identity.get_private_key().public_key(), algorithms=["RS256"])
        except ExpiredSignatureError:
            raise InvalidAccessTokenException("Token has expired")
        except InvalidTokenError:
            raise InvalidAccessTokenException("Token's cryptographic verification failed")

    @staticmethod
    def _get_identity_from_microsoft_identity(microsoft_identity: MicrosoftIdentity, ip_address: str | None = None, port_number: int | None = None) -> "Identity":
        return Identity(microsoft_identity=microsoft_identity, ip_address=ip_address, port_number=port_number)
