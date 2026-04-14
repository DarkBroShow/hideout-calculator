from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.routers import auth, auction, health, recipes
from app.services.stalcraft_client import StalcraftClient
from app.routers import debug as debug_router


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

    if settings.backend_debug:
        app.include_router(debug_router.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_level="info" if settings.app_debug else "warning",
    )