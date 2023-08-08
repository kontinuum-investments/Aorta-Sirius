import datetime
import json
from typing import Any, Dict, List

from msal import PublicClientApplication
from pydantic import BaseModel

from sirius import common
from sirius.communication.discord import TextChannel
from sirius.constants import EnvironmentVariable
from sirius.exceptions import ApplicationException


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
    async def get_token(scopes: List[str], notification_text_channel: TextChannel, client_id: str | None = None, tenant_id: str | None = None) -> "MicrosoftIdentityToken":
        client_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_CLIENT_ID) if client_id is None else client_id
        tenant_id = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID) if tenant_id is None else tenant_id
        public_client_application: PublicClientApplication = PublicClientApplication(client_id, authority=f"https://login.microsoftonline.com/{tenant_id}")

        flow: Dict[str, Any]
        authentication_flow: AuthenticationFlow
        flow, authentication_flow = MicrosoftIdentityToken._get_flow(public_client_application, scopes)

        await notification_text_channel.send_message(f"**Authentication Request**:\n"
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
