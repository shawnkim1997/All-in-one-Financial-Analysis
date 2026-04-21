"""Tests for Phase 3 envelope encryption."""

import os

import pytest
from fastapi.testclient import TestClient

from server.core.secrets import InvalidSecretBlob, SecretsVault, load_master_key_from_env
from server.main import app


def test_secrets_vault_round_trip() -> None:
    vault = SecretsVault(os.urandom(32))

    blob = vault.encrypt("kis-secret-value", user_id="local", provider="kis")

    assert blob != b"kis-secret-value"
    assert vault.decrypt(blob, user_id="local", provider="kis") == "kis-secret-value"


def test_secrets_vault_binds_blob_to_user_and_provider() -> None:
    vault = SecretsVault(os.urandom(32))
    blob = vault.encrypt("kis-secret-value", user_id="local", provider="kis")

    with pytest.raises(InvalidSecretBlob):
        vault.decrypt(blob, user_id="other", provider="kis")

    with pytest.raises(InvalidSecretBlob):
        vault.decrypt(blob, user_id="local", provider="ibkr")


def test_secrets_vault_detects_tampering() -> None:
    vault = SecretsVault(os.urandom(32))
    blob = bytearray(vault.encrypt("kis-secret-value", user_id="local", provider="kis"))
    blob[-1] ^= 1

    with pytest.raises(InvalidSecretBlob):
        vault.decrypt(bytes(blob), user_id="local", provider="kis")


def test_load_master_key_accepts_token_urlsafe_env(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_MASTER_KEY", "test-master-key-material")

    key = load_master_key_from_env()

    assert len(key) == 32


def test_credentials_routes_store_status_and_delete_without_exposing_secret(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_MASTER_KEY", "test-master-key-material")

    with TestClient(app) as client:
        stored = client.put("/api/credentials/kis", json={"user_id": "local", "secret": "kis-secret-value"})
        status = client.get("/api/credentials/kis/status?user_id=local")
        deleted = client.delete("/api/credentials/kis?user_id=local")
        after_delete = client.get("/api/credentials/kis/status?user_id=local")

    assert stored.status_code == 200
    assert stored.json() == {"user_id": "local", "provider": "kis", "stored": True}
    assert status.status_code == 200
    assert status.json()["configured"] is True
    assert "kis-secret-value" not in str(status.json())
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert after_delete.status_code == 200
    assert after_delete.json()["configured"] is False


def test_credentials_route_requires_master_key(monkeypatch) -> None:
    monkeypatch.delenv("ATLAS_MASTER_KEY", raising=False)

    with TestClient(app) as client:
        response = client.put("/api/credentials/kis", json={"user_id": "local", "secret": "kis-secret-value"})

    assert response.status_code == 503
    assert response.json()["detail"] == "ATLAS_MASTER_KEY is not configured"
