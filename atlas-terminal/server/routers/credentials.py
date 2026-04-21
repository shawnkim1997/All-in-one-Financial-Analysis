"""Secure credential storage routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from server.core.secrets import MissingMasterKey, SecretsError
from server.db.credentials_repo import delete_credential, get_credential_status, log_credential_access
from server.services.credentials_service import store_credential

router = APIRouter()


class CredentialUpsertRequest(BaseModel):
    secret: str = Field(min_length=1, description="Plaintext API secret. It is envelope-encrypted before storage.")
    user_id: str = Field(default="local", min_length=1)


def _request_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua


@router.put("/{provider}")
async def upsert_provider_credential(provider: str, body: CredentialUpsertRequest, request: Request) -> dict[str, object]:
    ip, ua = _request_meta(request)
    try:
        await store_credential(body.user_id, provider, body.secret, ip, ua)
    except MissingMasterKey as exc:
        raise HTTPException(status_code=503, detail="ATLAS_MASTER_KEY is not configured") from exc
    except SecretsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user_id": body.user_id, "provider": provider.lower(), "stored": True}


@router.get("/{provider}/status")
async def provider_credential_status(provider: str, request: Request, user_id: str = "local") -> dict[str, object]:
    ip, ua = _request_meta(request)
    row = await get_credential_status(user_id, provider)
    await log_credential_access(user_id, provider, "status", ip, ua)
    if not row:
        return {"user_id": user_id, "provider": provider.lower(), "configured": False}
    return {
        "user_id": user_id,
        "provider": provider.lower(),
        "configured": True,
        "created_at": row.get("created_at"),
        "last_used_at": row.get("last_used_at"),
    }


@router.delete("/{provider}")
async def delete_provider_credential(provider: str, request: Request, user_id: str = "local") -> dict[str, object]:
    ip, ua = _request_meta(request)
    deleted = await delete_credential(user_id, provider)
    await log_credential_access(user_id, provider, "delete", ip, ua)
    return {"user_id": user_id, "provider": provider.lower(), "deleted": deleted}
