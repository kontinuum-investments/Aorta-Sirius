import pytest

from sirius.iam.microsoft_entra_id import MicrosoftIdentityToken, MicrosoftIdentity


@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_validate_jwt_token() -> None:
    microsoft_identity: MicrosoftIdentity = await MicrosoftIdentityToken.is_access_token_valid("")
    assert microsoft_identity.name is not None
