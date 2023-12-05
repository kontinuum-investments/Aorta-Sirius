from urllib.parse import urlencode

import pytest

from sirius import common
from sirius.constants import EnvironmentSecret
from sirius.iam.microsoft_entra_id import MicrosoftIdentity


@pytest.mark.asyncio
async def test_get_login_url() -> None:
    authentication_id: str = common.get_unique_id()
    entra_id_tenant_id: str = common.get_environmental_secret(EnvironmentSecret.ENTRA_ID_TENANT_ID)
    entra_id_client_id: str = common.get_environmental_secret(EnvironmentSecret.ENTRA_ID_CLIENT_ID)
    redirect_url: str = "http://localhost/"
    url: str = MicrosoftIdentity.get_login_url(redirect_url, authentication_id)

    assert f"https://login.microsoftonline.com/{entra_id_tenant_id}/oauth2/v2.0/authorize?client_id={entra_id_client_id}&response_type=code&{urlencode({'redirect_uri': redirect_url})}&response_mode=query&scope=User.Read&state={authentication_id}" in url


@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_get_access_token() -> None:
    await MicrosoftIdentity.get_access_token_remotely("http://localhost/")


@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_validate_jwt_token() -> None:
    microsoft_identity: MicrosoftIdentity = MicrosoftIdentity.get_identity_from_access_token("")
    assert microsoft_identity.name is not None
