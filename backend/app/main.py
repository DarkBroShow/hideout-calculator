from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.routers import auth, auction, health, recipes
from app.services.stalcraft_client import StalcraftClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stalcraft_client = StalcraftClient()
    try:
        yield
    finally:
        await app.state.stalcraft_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(recipes.router)
    app.include_router(auction.router)

    return app


app = create_app()