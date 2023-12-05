import pytest

from sirius.iam import Identity


#   Use MicrosoftEntraIDAuthenticationIDStore.add(authentication_id, "") to manually add the access token in AuthenticationFlow.get_or_wait()
@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_get_access_token_remotely() -> None:
    access_token: str = await Identity.get_access_token_remotely("http://localhost:5000/ares/entra_id_response", "0.0.0.0", 0)
    assert access_token is not None


@pytest.mark.skip(reason="Requires Interaction")
@pytest.mark.asyncio
async def test_validate_access_token() -> None:
    identity: Identity = Identity.get_identity_from_access_token("")
    assert identity is not None
