from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAdmin, DBSession
from app.schemas.admin import AdminEnrollmentItem, AdminPurchaseItem
from app.schemas.category import CategoryCreateRequest, CategoryResponse
from app.schemas.common import MessageResponse, Page, SuccessResponse, build_page
from app.schemas.course import (
    CourseAdminResponse,
    CourseCreateRequest,
    CourseUpdateRequest,
)
from app.schemas.user import UserResponse
from app.services.category_service import CategoryService
from app.services.course_service import CourseService
from app.services.enrollment_service import EnrollmentService
from app.services.purchase_service import PurchaseService
from app.services.user_service import UserService

# Always-on admin surface: course + category management. Every route requires
# an authenticated admin (enforced per-endpoint via the CurrentAdmin dependency).
router = APIRouter(prefix="/admin", tags=["admin"])

# Admin listings for the deprecated modules — mounted only when their feature
# flag is on. Kept intact for a possible future reactivation.
accounts_router = APIRouter(prefix="/admin", tags=["admin"])  # ENABLE_ACCOUNTS
commerce_router = APIRouter(prefix="/admin", tags=["admin"])  # ENABLE_COMMERCE


# --- Courses --------------------------------------------------------------- #
@router.get("/courses", response_model=SuccessResponse[Page[CourseAdminResponse]])
async def list_courses_admin(
    _admin: CurrentAdmin,
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> SuccessResponse[Page[CourseAdminResponse]]:
    offset = (page - 1) * limit
    courses, total = await CourseService(session).list_admin(offset=offset, limit=limit)
    items = [CourseAdminResponse.model_validate(c) for c in courses]
    return SuccessResponse(data=build_page(items, total=total, page=page, limit=limit))


@router.post(
    "/courses",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[CourseAdminResponse],
)
async def create_course(
    payload: CourseCreateRequest, _admin: CurrentAdmin, session: DBSession
) -> SuccessResponse[CourseAdminResponse]:
    course = await CourseService(session).create_course(payload)
    return SuccessResponse(
        data=CourseAdminResponse.model_validate(course), message="Curso creado."
    )


@router.get(
    "/courses/{course_id}", response_model=SuccessResponse[CourseAdminResponse]
)
async def get_course_admin(
    course_id: uuid.UUID, _admin: CurrentAdmin, session: DBSession
) -> SuccessResponse[CourseAdminResponse]:
    course = await CourseService(session).get_or_404(course_id)
    return SuccessResponse(data=CourseAdminResponse.model_validate(course))


@router.patch(
    "/courses/{course_id}", response_model=SuccessResponse[CourseAdminResponse]
)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdateRequest,
    _admin: CurrentAdmin,
    session: DBSession,
) -> SuccessResponse[CourseAdminResponse]:
    course = await CourseService(session).update_course(course_id, payload)
    return SuccessResponse(
        data=CourseAdminResponse.model_validate(course), message="Curso actualizado."
    )


@router.delete("/courses/{course_id}", response_model=MessageResponse)
async def delete_course(
    course_id: uuid.UUID, _admin: CurrentAdmin, session: DBSession
) -> MessageResponse:
    await CourseService(session).delete_course(course_id)
    return MessageResponse(message="Curso eliminado.")


# --- Categories ------------------------------------------------------------ #
@router.post(
    "/categories",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[CategoryResponse],
)
async def create_category(
    payload: CategoryCreateRequest, _admin: CurrentAdmin, session: DBSession
) -> SuccessResponse[CategoryResponse]:
    category = await CategoryService(session).create(
        name=payload.name, description=payload.description
    )
    return SuccessResponse(
        data=CategoryResponse.model_validate(category), message="Categoría creada."
    )


# --- Users (accounts module) ----------------------------------------------- #
@accounts_router.get("/users", response_model=SuccessResponse[Page[UserResponse]])
async def list_users(
    _admin: CurrentAdmin,
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> SuccessResponse[Page[UserResponse]]:
    offset = (page - 1) * limit
    users, total = await UserService(session).list_users(offset=offset, limit=limit)
    items = [UserResponse.model_validate(u) for u in users]
    return SuccessResponse(data=build_page(items, total=total, page=page, limit=limit))


# --- Purchases (commerce module) ------------------------------------------- #
@commerce_router.get("/purchases", response_model=SuccessResponse[Page[AdminPurchaseItem]])
async def list_purchases(
    _admin: CurrentAdmin,
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> SuccessResponse[Page[AdminPurchaseItem]]:
    offset = (page - 1) * limit
    purchases, total = await PurchaseService(session).purchases.list_all(
        offset=offset, limit=limit
    )
    items = [
        AdminPurchaseItem(
            id=p.id,
            user_id=p.user_id,
            user_email=p.user.email,
            user_name=p.user.full_name,
            course_id=p.course_id,
            course_title=p.course.title,
            amount=p.amount,
            currency=p.currency,
            status=p.status,
            created_at=p.created_at,
        )
        for p in purchases
    ]
    return SuccessResponse(data=build_page(items, total=total, page=page, limit=limit))


# --- Enrollments (commerce module) ----------------------------------------- #
@commerce_router.get("/enrollments", response_model=SuccessResponse[Page[AdminEnrollmentItem]])
async def list_enrollments(
    _admin: CurrentAdmin,
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> SuccessResponse[Page[AdminEnrollmentItem]]:
    offset = (page - 1) * limit
    enrollments, total = await EnrollmentService(session).list_all(
        offset=offset, limit=limit
    )
    items = [
        AdminEnrollmentItem(
            id=e.id,
            user_id=e.user_id,
            user_email=e.user.email,
            course_id=e.course_id,
            course_title=e.course.title,
            status=e.status,
            enrolled_at=e.enrolled_at,
        )
        for e in enrollments
    ]
    return SuccessResponse(data=build_page(items, total=total, page=page, limit=limit))
