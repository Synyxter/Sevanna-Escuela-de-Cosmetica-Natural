from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_published_course(client: AsyncClient, admin_headers: dict) -> dict:
    course_payload = {
        "title": "Elaboración de Jabones",
        "short_description": "Jabones naturales desde cero",
        "modality": "HYBRID",
        "level": "BEGINNER",
        "price": "150000.00",
        "currency": "COP",
        "status": "PUBLISHED",
        "whatsapp_group_url": "https://chat.whatsapp.com/x",
        "google_meet_url": "https://meet.google.com/x",
    }
    resp = await client.post(
        "/api/v1/admin/courses", json=course_payload, headers=admin_headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def test_admin_can_create_course(client: AsyncClient, admin_headers: dict) -> None:
    course = await _create_published_course(client, admin_headers)
    assert course["slug"]  # slug auto-generated
    assert course["status"] == "PUBLISHED"


async def test_non_admin_cannot_create_course(
    client: AsyncClient, student_headers: dict
) -> None:
    resp = await client.post(
        "/api/v1/admin/courses",
        json={
            "title": "X",
            "modality": "ONLINE",
            "level": "BEGINNER",
            "price": "1000.00",
        },
        headers=student_headers,
    )
    assert resp.status_code == 403


async def test_public_catalog_lists_published(
    client: AsyncClient, admin_headers: dict
) -> None:
    await _create_published_course(client, admin_headers)
    resp = await client.get("/api/v1/courses?page=1&limit=10")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["pagination"]["total"] == 1
    assert len(data["items"]) == 1
    # Private links must NOT appear in the public catalog item.
    assert "whatsapp_group_url" not in data["items"][0]


async def test_course_detail_by_slug_hides_private_links(
    client: AsyncClient, admin_headers: dict
) -> None:
    course = await _create_published_course(client, admin_headers)
    resp = await client.get(f"/api/v1/courses/{course['slug']}")
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["title"] == "Elaboración de Jabones"
    assert "whatsapp_group_url" not in detail
    assert "google_meet_url" not in detail


async def test_draft_course_not_public(client: AsyncClient, admin_headers: dict) -> None:
    resp = await client.post(
        "/api/v1/admin/courses",
        json={
            "title": "Borrador",
            "modality": "ONLINE",
            "level": "BEGINNER",
            "price": "5000.00",
            "status": "DRAFT",
        },
        headers=admin_headers,
    )
    slug = resp.json()["data"]["slug"]
    # Not in catalog
    catalog = await client.get("/api/v1/courses")
    assert catalog.json()["data"]["pagination"]["total"] == 0
    # Not accessible by slug publicly
    detail = await client.get(f"/api/v1/courses/{slug}")
    assert detail.status_code == 404


async def test_catalog_filters_by_level(client: AsyncClient, admin_headers: dict) -> None:
    await _create_published_course(client, admin_headers)  # BEGINNER
    resp = await client.get("/api/v1/courses?level=ADVANCED")
    assert resp.json()["data"]["pagination"]["total"] == 0
