from fastapi import APIRouter, Query

from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config")
async def auth_config():
    return {
        "client_id": settings.stalcraft_client_id,
        "region": settings.stalcraft_region,
        "redirect_uri": settings.oauth_redirect_uri,
    }


@router.get("/callback")
async def auth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
):
    return {
        "message": "OAuth callback received",
        "code": code,
        "state": state,
    }