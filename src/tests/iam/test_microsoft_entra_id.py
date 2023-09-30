from urllib.parse import urlencode

import pytest

from sirius import common
from sirius.constants import EnvironmentVariable
from sirius.http_requests import ClientSideException
from sirius.iam.microsoft_entra_id import MicrosoftIdentity


@pytest.mark.asyncio
async def test_get_login_url() -> None:
    authentication_id: str = common.get_unique_id()
    entra_id_tenant_id: str = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_TENANT_ID)
    entra_id_client_id: str = common.get_environmental_variable(EnvironmentVariable.ENTRA_ID_CLIENT_ID)
    redirect_url: str = "http://localhost/"
    url: str = MicrosoftIdentity.get_login_url(redirect_url, authentication_id)

    assert url == f"https://login.microsoftonline.com/{entra_id_tenant_id}/oauth2/v2.0/authorize?client_id={entra_id_client_id}&response_type=code&{urlencode({'redirect_uri': redirect_url})}&response_mode=query&scope=User.Read&state={authentication_id}"


@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_get_access_token() -> None:
    await MicrosoftIdentity.get_access_token("", "http://localhost/")


@pytest.mark.asyncio
async def test_get_access_token_with_invalid_code() -> None:
    with pytest.raises(ClientSideException):
        await MicrosoftIdentity.get_access_token("", "http://localhost/")


@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_validate_jwt_token() -> None:
    microsoft_identity: MicrosoftIdentity = await MicrosoftIdentity.get_identity_from_access_token("")
    assert microsoft_identity.name is not None
