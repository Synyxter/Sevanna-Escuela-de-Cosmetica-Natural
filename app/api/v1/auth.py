from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.deps import DBSession
from app.core.rate_limit import (
    forgot_password_rate_limit,
    login_rate_limit,
    register_rate_limit,
)
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenPair,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse, SuccessResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=SuccessResponse[UserResponse],
    dependencies=[Depends(register_rate_limit)],
)
async def register(
    payload: RegisterRequest,
    session: DBSession,
    background: BackgroundTasks,
) -> SuccessResponse[UserResponse]:
    user = await AuthService(session).register(
        full_name=payload.full_name,
        email=payload.email,
        password=payload.password,
        background=background,
    )
    return SuccessResponse(
        data=UserResponse.model_validate(user),
        message="Registro exitoso. Revisa tu correo para verificar la cuenta.",
    )


@router.post(
    "/login",
    response_model=SuccessResponse[TokenPair],
    dependencies=[Depends(login_rate_limit)],
)
async def login(
    payload: LoginRequest, session: DBSession
) -> SuccessResponse[TokenPair]:
    _, tokens = await AuthService(session).login(
        email=payload.email, password=payload.password
    )
    return SuccessResponse(data=tokens, message="Inicio de sesión exitoso.")


@router.post("/refresh", response_model=SuccessResponse[TokenPair])
async def refresh(payload: RefreshRequest, session: DBSession) -> SuccessResponse[TokenPair]:
    tokens = await AuthService(session).refresh(payload.refresh_token)
    return SuccessResponse(data=tokens, message="Sesión renovada.")


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: LogoutRequest, session: DBSession) -> MessageResponse:
    await AuthService(session).logout(payload.refresh_token)
    return MessageResponse(message="Sesión cerrada.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest, session: DBSession) -> MessageResponse:
    await AuthService(session).verify_email(token=payload.token)
    return MessageResponse(message="Correo verificado correctamente.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    dependencies=[Depends(forgot_password_rate_limit)],
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: DBSession,
    background: BackgroundTasks,
) -> MessageResponse:
    message = await AuthService(session).forgot_password(
        email=payload.email, background=background
    )
    return MessageResponse(message=message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest, session: DBSession
) -> MessageResponse:
    await AuthService(session).reset_password(
        token=payload.token, new_password=payload.new_password
    )
    return MessageResponse(message="Contraseña actualizada correctamente.")
