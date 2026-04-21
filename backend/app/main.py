from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from app.core.config import settings
from app.db.base import async_session_factory, engine
from app.db.importer import run_import
from app.db import models
from app.routers import auth, auction, health, recipes, items
from app.services.stalcraft_client import StalcraftClient
from app.services.db_updater import ensure_repo, watch_for_updates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Клонирование репозитория и подключение иконок
    ensure_repo()

    icons_path = Path(settings.stalcraft_db_path) / settings.stalcraft_region / "icons"
    if icons_path.exists():
        app.mount("/icons", StaticFiles(directory=str(icons_path)), name="icons")
    else:
        import logging
        logging.getLogger(__name__).warning("icons path not found after ensure_repo: %s", icons_path)

    # 2. Создать таблицы
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    # 3. Импорт данных
    async with async_session_factory() as session:
        await run_import(session, region=settings.stalcraft_region)

    # 4. Фоновый мониторинг
    watcher_task = asyncio.create_task(watch_for_updates())

    app.state.stalcraft_client = StalcraftClient()
    try:
        yield
    finally:
        watcher_task.cancel()
        await app.state.stalcraft_client.aclose()
        await engine.dispose()


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
    app.include_router(items.router)
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