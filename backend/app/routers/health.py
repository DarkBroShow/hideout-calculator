from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def healthcheck():
    return HealthResponse(
        status="ok",
        app=settings.app_name,
    )