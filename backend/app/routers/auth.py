from fastapi import APIRouter, Query
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

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