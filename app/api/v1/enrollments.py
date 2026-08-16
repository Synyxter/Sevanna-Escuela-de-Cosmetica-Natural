from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import SuccessResponse
from app.schemas.enrollment import EnrollmentAccessResponse, EnrollmentResponse
from app.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.get("/{enrollment_id}", response_model=SuccessResponse[EnrollmentResponse])
async def get_enrollment(
    enrollment_id: uuid.UUID, current_user: CurrentUser, session: DBSession
) -> SuccessResponse[EnrollmentResponse]:
    enrollment = await EnrollmentService(session).get_for_user(
        enrollment_id=enrollment_id, user=current_user
    )
    return SuccessResponse(data=EnrollmentResponse.model_validate(enrollment))


@router.get(
    "/{enrollment_id}/access",
    response_model=SuccessResponse[EnrollmentAccessResponse],
)
async def enrollment_access(
    enrollment_id: uuid.UUID, current_user: CurrentUser, session: DBSession
) -> SuccessResponse[EnrollmentAccessResponse]:
    """Private WhatsApp/Google Meet links — only for the active enrollment's owner."""
    whatsapp_url, google_meet_url = await EnrollmentService(session).get_access_links(
        enrollment_id=enrollment_id, user=current_user
    )
    return SuccessResponse(
        data=EnrollmentAccessResponse(
            whatsapp_url=whatsapp_url, google_meet_url=google_meet_url
        )
    )
