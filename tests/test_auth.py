from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_creates_student(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ana López",
            "email": "ana@example.com",
            "password": "SuperSecret1",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["email"] == "ana@example.com"
    assert body["data"]["role"] == "STUDENT"
    assert body["data"]["email_verified"] is False
    # Never leak the password hash.
    assert "password_hash" not in body["data"]


async def test_register_duplicate_email_conflicts(client: AsyncClient) -> None:
    payload = {
        "full_name": "Ana",
        "email": "dup@example.com",
        "password": "SuperSecret1",
    }
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409
    assert second.json()["success"] is False


async def test_login_and_me(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Leo", "email": "leo@example.com", "password": "SuperSecret1"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "leo@example.com", "password": "SuperSecret1"},
    )
    assert login.status_code == 200
    tokens = login.json()["data"]
    assert tokens["access_token"] and tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = await client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["data"]["email"] == "leo@example.com"


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Mia", "email": "mia@example.com", "password": "SuperSecret1"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "mia@example.com", "password": "wrongpass1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_ERROR"


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401


async def test_refresh_rotates_token(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Sam", "email": "sam@example.com", "password": "SuperSecret1"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "sam@example.com", "password": "SuperSecret1"},
    )
    refresh_token = login.json()["data"]["refresh_token"]
    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refreshed.status_code == 200
    # Old refresh token is revoked after rotation.
    reused = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reused.status_code == 401
