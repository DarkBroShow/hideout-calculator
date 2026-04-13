from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, auction, health, recipes


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(recipes.router)
    app.include_router(auction.router)

    return app


app = create_app()