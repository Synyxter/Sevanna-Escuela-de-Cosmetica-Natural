from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import DBSession
from app.models.enums import CourseLevel, CourseModality
from app.schemas.common import Page, SuccessResponse, build_page
from app.schemas.course import (
    CourseDetailResponse,
    CourseFilterParams,
    CourseListItem,
)
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=SuccessResponse[Page[CourseListItem]])
async def list_courses(
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    search: str | None = Query(None, max_length=200),
    category: str | None = Query(None, description="Category slug"),
    level: CourseLevel | None = Query(None),
    modality: CourseModality | None = Query(None),
    sort: str = Query("-created_at", description="Sort field, prefix '-' for descending"),
) -> SuccessResponse[Page[CourseListItem]]:
    """Public catalog with pagination, search, filtering and sorting.

    Only PUBLISHED courses are returned; private links are never exposed here.
    """
    filters = CourseFilterParams(
        page=page,
        limit=limit,
        search=search,
        category=category,
        level=level,
        modality=modality,
        sort=sort,
    )
    courses, total = await CourseService(session).list_catalog(filters)
    items = [CourseListItem.model_validate(c) for c in courses]
    return SuccessResponse(data=build_page(items, total=total, page=page, limit=limit))


@router.get("/featured", response_model=SuccessResponse[list[CourseListItem]])
async def featured_courses(
    session: DBSession, limit: int = Query(6, ge=1, le=20)
) -> SuccessResponse[list[CourseListItem]]:
    courses = await CourseService(session).list_featured(limit)
    return SuccessResponse(data=[CourseListItem.model_validate(c) for c in courses])


@router.get("/{slug}", response_model=SuccessResponse[CourseDetailResponse])
async def course_detail(
    slug: str, session: DBSession
) -> SuccessResponse[CourseDetailResponse]:
    course = await CourseService(session).get_public_by_slug(slug)
    return SuccessResponse(data=CourseDetailResponse.model_validate(course))
