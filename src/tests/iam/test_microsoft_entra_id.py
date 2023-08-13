import pytest

from sirius.iam.microsoft_entra_id import MicrosoftIdentity


@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_validate_jwt_token() -> None:
    microsoft_identity: MicrosoftIdentity = await MicrosoftIdentity.get_identity_from_access_token("")
    assert microsoft_identity.name is not None
