import base64

import pyotp


class TwoFactorAuthentication:

    @staticmethod
    def get_authenticator_uri(username: str, issuer_name: str, hash_str: str | None) -> str:
        hash_str = pyotp.random_base32() if hash_str is None else base64.b32encode(hash_str.encode("UTF-8")).decode("UTF-8")
        return pyotp.totp.TOTP(hash_str).provisioning_uri(name=username, issuer_name=issuer_name)

    @staticmethod
    def get_otp(hash_str: str) -> str:
        return pyotp.TOTP(base64.b32encode(hash_str.encode("UTF-8")).decode("UTF-8")).now()

    @staticmethod
    def is_otp_valid(otp: str, hash_str: str) -> bool:
        return pyotp.TOTP(base64.b32encode(hash_str.encode("UTF-8")).decode("UTF-8")).verify(otp)
