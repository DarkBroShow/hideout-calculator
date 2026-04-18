from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.services.db_updater import state as updater_state

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def healthcheck():
    return HealthResponse(
        status="maintenance" if updater_state.maintenance else "ok",
        app=settings.app_name,
        maintenance=updater_state.maintenance,
        db_commit=updater_state.last_commit,
    )