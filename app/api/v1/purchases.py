from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.common import SuccessResponse
from app.schemas.purchase import PurchaseCreateRequest, PurchaseResponse
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/purchases", tags=["purchases"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[PurchaseResponse],
)
async def create_purchase(
    payload: PurchaseCreateRequest, current_user: CurrentUser, session: DBSession
) -> SuccessResponse[PurchaseResponse]:
    purchase = await PurchaseService(session).create_purchase(
        user=current_user, course_id=payload.course_id
    )
    return SuccessResponse(
        data=PurchaseResponse.model_validate(purchase),
        message="Compra iniciada. Continúa con el pago.",
    )


@router.get("/{purchase_id}", response_model=SuccessResponse[PurchaseResponse])
async def get_purchase(
    purchase_id: uuid.UUID, current_user: CurrentUser, session: DBSession
) -> SuccessResponse[PurchaseResponse]:
    purchase = await PurchaseService(session).get_for_user(
        purchase_id=purchase_id, user=current_user
    )
    return SuccessResponse(data=PurchaseResponse.model_validate(purchase))
