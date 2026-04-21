"""Envelope encryption utilities for locally stored API credentials."""

from __future__ import annotations

import base64
import hashlib
import os
import struct
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"ATLASV1"
NONCE_SIZE = 12
DEK_SIZE = 32


class SecretsError(Exception):
    """Base class for credential encryption failures."""


class MissingMasterKey(SecretsError):
    """Raised when ATLAS_MASTER_KEY is required but not configured."""


class InvalidSecretBlob(SecretsError):
    """Raised when an encrypted credential blob is malformed or cannot decrypt."""


def _decode_master_key(value: str) -> bytes:
    raw = value.strip()
    if not raw:
        raise MissingMasterKey("ATLAS_MASTER_KEY is empty")

    for candidate in (
        raw,
        raw + "=" * (-len(raw) % 4),
    ):
        try:
            decoded = base64.urlsafe_b64decode(candidate.encode("utf-8"))
            if len(decoded) == DEK_SIZE:
                return decoded
        except Exception:
            pass

    try:
        decoded_hex = bytes.fromhex(raw)
        if len(decoded_hex) == DEK_SIZE:
            return decoded_hex
    except ValueError:
        pass

    # Allow token_urlsafe strings of any supported length while still handing
    # AES-GCM a fixed-width key.  The raw env var remains the root secret.
    return hashlib.sha256(raw.encode("utf-8")).digest()


def load_master_key_from_env(env_var: str = "ATLAS_MASTER_KEY") -> bytes:
    value = os.getenv(env_var, "")
    if not value.strip():
        raise MissingMasterKey(f"{env_var} is not configured")
    return _decode_master_key(value)


@dataclass(frozen=True)
class SecretsVault:
    """Envelope encryption vault.

    Format:
    MAGIC || key_nonce || data_nonce || encrypted_dek_len:uint16 ||
    encrypted_dek || ciphertext
    """

    master_key: bytes

    @classmethod
    def from_env(cls) -> "SecretsVault":
        return cls(load_master_key_from_env())

    def __post_init__(self) -> None:
        if len(self.master_key) not in {16, 24, 32}:
            raise ValueError("master_key must be 16, 24, or 32 bytes for AES-GCM")

    def _aad(self, user_id: str, provider: str) -> bytes:
        return f"{user_id.strip()}:{provider.strip().lower()}".encode("utf-8")

    def encrypt(self, plaintext: str, user_id: str, provider: str = "kis") -> bytes:
        if not plaintext:
            raise ValueError("plaintext must not be empty")

        dek = os.urandom(DEK_SIZE)
        key_nonce = os.urandom(NONCE_SIZE)
        data_nonce = os.urandom(NONCE_SIZE)
        aad = self._aad(user_id, provider)

        encrypted_dek = AESGCM(self.master_key).encrypt(key_nonce, dek, aad)
        ciphertext = AESGCM(dek).encrypt(data_nonce, plaintext.encode("utf-8"), aad)

        return b"".join(
            [
                MAGIC,
                key_nonce,
                data_nonce,
                struct.pack("!H", len(encrypted_dek)),
                encrypted_dek,
                ciphertext,
            ]
        )

    def decrypt(self, encrypted_blob: bytes, user_id: str, provider: str = "kis") -> str:
        try:
            if not encrypted_blob.startswith(MAGIC):
                raise InvalidSecretBlob("invalid secret blob header")
            offset = len(MAGIC)
            key_nonce = encrypted_blob[offset : offset + NONCE_SIZE]
            offset += NONCE_SIZE
            data_nonce = encrypted_blob[offset : offset + NONCE_SIZE]
            offset += NONCE_SIZE
            encrypted_dek_len = struct.unpack("!H", encrypted_blob[offset : offset + 2])[0]
            offset += 2
            encrypted_dek = encrypted_blob[offset : offset + encrypted_dek_len]
            offset += encrypted_dek_len
            ciphertext = encrypted_blob[offset:]

            if len(key_nonce) != NONCE_SIZE or len(data_nonce) != NONCE_SIZE or not encrypted_dek or not ciphertext:
                raise InvalidSecretBlob("truncated secret blob")

            aad = self._aad(user_id, provider)
            dek = AESGCM(self.master_key).decrypt(key_nonce, encrypted_dek, aad)
            plaintext = AESGCM(dek).decrypt(data_nonce, ciphertext, aad)
            return plaintext.decode("utf-8")
        except InvalidSecretBlob:
            raise
        except Exception as exc:
            raise InvalidSecretBlob("secret blob could not be decrypted") from exc
