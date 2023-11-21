import base64
import urllib.parse

from sirius import common
from sirius.iam.two_factor_authentication import TwoFactorAuthentication


def test_get_authenticator_uri() -> None:
    name: str = "John Doe"
    issuer_name: str = "Test Application"
    hash_str: str = common.get_unique_id()
    assert TwoFactorAuthentication.get_authenticator_uri(name, issuer_name, hash_str) == f"otpauth://totp/{urllib.parse.quote(issuer_name)}:{urllib.parse.quote(name)}?secret={urllib.parse.quote(base64.b32encode(hash_str.encode('UTF-8')).decode('UTF-8'))}&issuer={urllib.parse.quote(issuer_name)}"


def test_is_otp_valid() -> None:
    hash_str: str = common.get_unique_id()
    assert TwoFactorAuthentication.is_otp_valid(TwoFactorAuthentication.get_otp(hash_str), hash_str)
