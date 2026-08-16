from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api.deps import CurrentUser, DBSession
from app.core.exceptions import ValidationError
from app.core.rate_limit import payment_rate_limit, webhook_rate_limit
from app.integrations.payments.base import InvalidWebhookError
from app.schemas.common import SuccessResponse
from app.schemas.payment import (
    PaymentCreateRequest,
    PaymentInitResponse,
    PaymentResponse,
    WebhookResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[PaymentInitResponse],
    dependencies=[Depends(payment_rate_limit)],
)
async def create_payment(
    payload: PaymentCreateRequest,
    current_user: CurrentUser,
    session: DBSession,
) -> SuccessResponse[PaymentInitResponse]:
    payment = await PaymentService(session).create_payment(
        purchase_id=payload.purchase_id, user=current_user
    )
    return SuccessResponse(
        data=PaymentInitResponse(
            payment_id=payment.id,
            checkout_url=payment.checkout_url,
            reference=payment.external_reference,
            status=payment.status,
        ),
        message="Pago creado. Redirige al usuario al proveedor.",
    )


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    dependencies=[Depends(webhook_rate_limit)],
)
async def payment_webhook(
    request: Request, session: DBSession, background: BackgroundTasks
) -> WebhookResponse:
    """Provider webhook. The raw body is validated against the provider signature.

    The source of truth for payment state — the frontend is never trusted.
    Returns 200 for authenticated events (processed or idempotently ignored);
    422 (INVALID_WEBHOOK) for spoofed/invalid signatures.
    """
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        processed, detail = await PaymentService(session).process_webhook(
            raw_body=raw_body, headers=headers, background=background
        )
    except InvalidWebhookError as exc:
        raise ValidationError(
            "Webhook inválido.", code="INVALID_WEBHOOK"
        ) from exc
    return WebhookResponse(received=True, processed=processed, detail=detail)


@router.get("/{payment_id}", response_model=SuccessResponse[PaymentResponse])
async def get_payment(
    payment_id: uuid.UUID, current_user: CurrentUser, session: DBSession
) -> SuccessResponse[PaymentResponse]:
    payment = await PaymentService(session).get_for_user(
        payment_id=payment_id, user=current_user
    )
    return SuccessResponse(data=PaymentResponse.model_validate(payment))
