from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/env")
def debug_env():
    return {
        "ports": {
            "app_port": settings.app_port,
            "postgres_port": settings.postgres_port,
        },
        "db": {
            "user": settings.postgres_user,
            "host": settings.postgres_host,
            "url": str(settings.database_url),
        },
        "stalcraft": {
            "region": settings.stalcraft_region,
            "client_id": settings.stalcraft_client_id,
            "redirect_uri": str(settings.oauth_redirect_uri),
        },
    }