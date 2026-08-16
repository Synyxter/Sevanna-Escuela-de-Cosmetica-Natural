from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DBSession
from app.schemas.category import CategoryResponse
from app.schemas.common import SuccessResponse
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=SuccessResponse[list[CategoryResponse]])
async def list_categories(session: DBSession) -> SuccessResponse[list[CategoryResponse]]:
    categories = await CategoryService(session).list_categories()
    return SuccessResponse(
        data=[CategoryResponse.model_validate(c) for c in categories]
    )
