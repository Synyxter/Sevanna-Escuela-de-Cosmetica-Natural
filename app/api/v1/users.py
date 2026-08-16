from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import Page, SuccessResponse, build_page
from app.schemas.enrollment import MyCourseItem
from app.schemas.purchase import PurchaseWithCourseResponse
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.enrollment_service import EnrollmentService
from app.services.purchase_service import PurchaseService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def get_me(current_user: CurrentUser) -> SuccessResponse[UserResponse]:
    return SuccessResponse(data=UserResponse.model_validate(current_user))


@router.patch("/me", response_model=SuccessResponse[UserResponse])
async def update_me(
    payload: UserUpdateRequest, current_user: CurrentUser, session: DBSession
) -> SuccessResponse[UserResponse]:
    user = await UserService(session).update_profile(
        current_user, full_name=payload.full_name
    )
    return SuccessResponse(
        data=UserResponse.model_validate(user), message="Perfil actualizado."
    )


@router.get("/me/courses", response_model=SuccessResponse[Page[MyCourseItem]])
async def my_courses(
    current_user: CurrentUser,
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
) -> SuccessResponse[Page[MyCourseItem]]:
    offset = (page - 1) * limit
    enrollments, total = await EnrollmentService(session).list_my_courses(
        user=current_user, offset=offset, limit=limit
    )
    items = [
        MyCourseItem(
            enrollment_id=e.id,
            course_id=e.course_id,
            title=e.course.title,
            slug=e.course.slug,
            image_url=e.course.image_url,
            modality=e.course.modality,
            status=e.status,
            enrolled_at=e.enrolled_at,
        )
        for e in enrollments
    ]
    return SuccessResponse(data=build_page(items, total=total, page=page, limit=limit))


@router.get(
    "/me/purchases", response_model=SuccessResponse[Page[PurchaseWithCourseResponse]]
)
async def my_purchases(
    current_user: CurrentUser,
    session: DBSession,
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
) -> SuccessResponse[Page[PurchaseWithCourseResponse]]:
    offset = (page - 1) * limit
    purchases, total = await PurchaseService(session).list_for_user(
        user=current_user, offset=offset, limit=limit
    )
    items = [
        PurchaseWithCourseResponse(
            id=p.id,
            course_id=p.course_id,
            amount=p.amount,
            currency=p.currency,
            status=p.status,
            created_at=p.created_at,
            course_title=p.course.title,
            course_slug=p.course.slug,
        )
        for p in purchases
    ]
    return SuccessResponse(data=build_page(items, total=total, page=page, limit=limit))
