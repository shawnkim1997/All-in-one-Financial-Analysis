"""High-level credential storage helpers."""

from __future__ import annotations

from server.core.secrets import SecretsVault
from server.db.credentials_repo import (
    get_credential_blob,
    log_credential_access,
    mark_credential_used,
    upsert_credential,
)


async def store_credential(
    user_id: str,
    provider: str,
    secret: str,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    vault = SecretsVault.from_env()
    encrypted = vault.encrypt(secret, user_id=user_id, provider=provider)
    await upsert_credential(user_id, provider, encrypted)
    await log_credential_access(user_id, provider, "upsert", ip, ua)


async def load_credential_secret(
    user_id: str,
    provider: str,
    ip: str | None = None,
    ua: str | None = None,
) -> str | None:
    blob = await get_credential_blob(user_id, provider)
    if blob is None:
        await log_credential_access(user_id, provider, "miss", ip, ua)
        return None
    secret = SecretsVault.from_env().decrypt(blob, user_id=user_id, provider=provider)
    await mark_credential_used(user_id, provider)
    await log_credential_access(user_id, provider, "decrypt", ip, ua)
    return secret
