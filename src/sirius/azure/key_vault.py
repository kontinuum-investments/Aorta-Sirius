import base64
import hashlib
import json
from typing import Dict, Any

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys import KeyClient, KeyVaultKey, KeyType
from azure.keyvault.keys.crypto import CryptographyClient, SignatureAlgorithm, SignResult, EncryptionAlgorithm
from azure.keyvault.secrets import SecretClient

from sirius import common
from sirius.constants import EnvironmentVariable
from sirius.exceptions import SDKClientException

secret_cache: Dict[str, str] = {}
key_cache: Dict[str, KeyVaultKey] = {}


class AzureKeyVault:
    secret_client: SecretClient | None = None
    key_client: KeyClient | None = None

    @classmethod
    def authenticate(cls) -> None:
        if cls.secret_client is not None and cls.key_client is not None:
            return

        cls.secret_client = SecretClient(vault_url=common.get_environmental_variable(EnvironmentVariable.AZURE_KEY_VAULT_URL), credential=DefaultAzureCredential())
        cls.key_client = KeyClient(vault_url=common.get_environmental_variable(EnvironmentVariable.AZURE_KEY_VAULT_URL), credential=DefaultAzureCredential())

    @classmethod
    def get(cls, key: str) -> str:
        global secret_cache
        if key in secret_cache:
            return secret_cache[key]

        cls.authenticate()
        try:
            value: str = cls.secret_client.get_secret(key).value
        except ResourceNotFoundError:
            raise SDKClientException("Secret not found: " + key)

        secret_cache[key] = value
        return value

    @classmethod
    def set(cls, key: str, value: str) -> None:
        cls.authenticate()
        cls.secret_client.set_secret(key, value)

        global secret_cache
        secret_cache[key] = value

    @classmethod
    def delete(cls, key: str) -> None:
        cls.authenticate()
        cls.secret_client.begin_delete_secret(key).result()

        global cacheecr
        if key in secret_cache:
            secret_cache.pop(key)

    @classmethod
    def get_key(cls, key_name: str, is_generate_if_unavailable: bool = False) -> KeyVaultKey:
        global key_cache
        if key_name in key_cache:
            return key_cache[key_name]

        cls.authenticate()

        try:
            azure_key: KeyVaultKey = cls.key_client.get_key(key_name)
        except ResourceNotFoundError:
            if is_generate_if_unavailable:
                return AzureKeyVault.create_key(key_name)
            else:
                raise SDKClientException("Key not found: " + key_name)

        key_cache[key_name] = azure_key
        return azure_key

    @classmethod
    def create_key(cls, key_name: str) -> KeyVaultKey:
        global key_cache
        cls.authenticate()

        azure_key: KeyVaultKey = cls.key_client.create_key(key_name, size=4096, key_type=KeyType.rsa)
        key_cache[key_name] = azure_key
        return azure_key

    @classmethod
    def delete_key(cls, key_name: str) -> None:
        global key_cache
        cls.authenticate()
        cls.key_client.begin_delete_key(key_name).result()
        key_cache.pop(key_name)


class AzureKeyVaultCryptography:
    @staticmethod
    def get_encrypted_data(key_name: str, data: bytes) -> bytes:
        azure_key: KeyVaultKey = AzureKeyVault.get_key(key_name, True)
        crypto_client: CryptographyClient = CryptographyClient(azure_key, DefaultAzureCredential())
        return crypto_client.encrypt(EncryptionAlgorithm.rsa_oaep_256, data).ciphertext

    @staticmethod
    def get_decrypted_data(key_name: str, encrypted_data: bytes) -> bytes:
        azure_key: KeyVaultKey = AzureKeyVault.get_key(key_name, True)
        crypto_client: CryptographyClient = CryptographyClient(azure_key, DefaultAzureCredential())
        return crypto_client.decrypt(EncryptionAlgorithm.rsa_oaep_256, encrypted_data).plaintext

    @staticmethod
    def get_jwt_token(key_name: str, payload: Dict[str, Any], header: Dict[str, Any] | None = None) -> str:
        header = {} if header is None else header
        header["alg"] = "RS256"
        header["typ"] = "JWT"

        azure_key: KeyVaultKey = AzureKeyVault.get_key(key_name, True)
        crypto_client: CryptographyClient = CryptographyClient(azure_key, DefaultAzureCredential())
        header_encoded: str = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_encoded: str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

        hash_var = hashlib.sha256()
        hash_var.update(f"{header_encoded}.{payload_encoded}".encode("utf-8"))

        sign_result: SignResult = crypto_client.sign(SignatureAlgorithm.rs256, hash_var.digest())
        signature: str = base64.urlsafe_b64encode(sign_result.signature).decode().rstrip("=")
        return f"{header_encoded}.{payload_encoded}.{signature}"
