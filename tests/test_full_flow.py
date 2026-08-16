"""End-to-end integration test of the core Sevanna flow.

Create course -> register/login student -> start purchase -> create payment ->
provider webhook confirms -> enrollment created -> my-courses -> private access.
Also verifies webhook idempotency (Rule 7/34) and frozen purchase price (Rule 30).
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

WEBHOOK_HEADERS = {"X-Fake-Signature": "fake-secret"}


async def _publish_course(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post(
        "/api/v1/admin/courses",
        json={
            "title": "Velas Aromáticas",
            "modality": "ONLINE",
            "level": "INTERMEDIATE",
            "price": "150000.00",
            "currency": "COP",
            "status": "PUBLISHED",
            "whatsapp_group_url": "https://chat.whatsapp.com/velas",
            "google_meet_url": "https://meet.google.com/velas",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def test_full_purchase_flow(
    client: AsyncClient, admin_headers: dict, student_headers: dict
) -> None:
    course = await _publish_course(client, admin_headers)

    # 1. Student starts a purchase — price is frozen from the backend.
    purchase_resp = await client.post(
        "/api/v1/purchases",
        json={"course_id": course["id"]},
        headers=student_headers,
    )
    assert purchase_resp.status_code == 201, purchase_resp.text
    purchase = purchase_resp.json()["data"]
    assert purchase["status"] == "PENDING"
    # Frozen price from the backend (compare numerically to be storage-agnostic).
    assert float(purchase["amount"]) == 150000.0

    # 2. Create the payment (fake provider).
    payment_resp = await client.post(
        "/api/v1/payments/create",
        json={"purchase_id": purchase["id"]},
        headers=student_headers,
    )
    assert payment_resp.status_code == 201, payment_resp.text
    payment = payment_resp.json()["data"]
    reference = payment["reference"]
    assert payment["checkout_url"]

    # 3. Provider confirms via webhook (source of truth).
    webhook_body = json.dumps(
        {"reference": reference, "status": "APPROVED", "amount": "150000.00", "currency": "COP"}
    )
    wh = await client.post(
        "/api/v1/payments/webhook", content=webhook_body, headers=WEBHOOK_HEADERS
    )
    assert wh.status_code == 200, wh.text
    assert wh.json()["processed"] is True
    assert wh.json()["detail"] == "paid"

    # 4. my-courses now shows the course.
    mine = await client.get("/api/v1/users/me/courses", headers=student_headers)
    assert mine.status_code == 200
    items = mine.json()["data"]["items"]
    assert len(items) == 1
    enrollment_id = items[0]["enrollment_id"]
    assert items[0]["course_id"] == course["id"]

    # 5. Private access links are available to the enrolled owner.
    access = await client.get(
        f"/api/v1/enrollments/{enrollment_id}/access", headers=student_headers
    )
    assert access.status_code == 200
    links = access.json()["data"]
    assert links["whatsapp_url"] == "https://chat.whatsapp.com/velas"
    assert links["google_meet_url"] == "https://meet.google.com/velas"

    # 6. Idempotency: a duplicate webhook does not create a second enrollment.
    wh2 = await client.post(
        "/api/v1/payments/webhook", content=webhook_body, headers=WEBHOOK_HEADERS
    )
    assert wh2.status_code == 200
    assert wh2.json()["processed"] is False
    assert wh2.json()["detail"] == "already_processed"

    mine_again = await client.get("/api/v1/users/me/courses", headers=student_headers)
    assert len(mine_again.json()["data"]["items"]) == 1


async def test_webhook_rejects_invalid_signature(
    client: AsyncClient, admin_headers: dict, student_headers: dict
) -> None:
    course = await _publish_course(client, admin_headers)
    purchase = (
        await client.post(
            "/api/v1/purchases", json={"course_id": course["id"]}, headers=student_headers
        )
    ).json()["data"]
    payment = (
        await client.post(
            "/api/v1/payments/create",
            json={"purchase_id": purchase["id"]},
            headers=student_headers,
        )
    ).json()["data"]

    body = json.dumps({"reference": payment["reference"], "status": "APPROVED"})
    resp = await client.post(
        "/api/v1/payments/webhook",
        content=body,
        headers={"X-Fake-Signature": "WRONG"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_WEBHOOK"


async def test_cannot_access_unpurchased_course_links(
    client: AsyncClient, admin_headers: dict, student_headers: dict
) -> None:
    # No purchase -> no enrollment -> accessing a random enrollment fails.
    resp = await client.get(
        "/api/v1/enrollments/00000000-0000-0000-0000-000000000000/access",
        headers=student_headers,
    )
    assert resp.status_code == 404


async def test_access_denied_without_auth(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/enrollments/00000000-0000-0000-0000-000000000000/access"
    )
    assert resp.status_code == 401
