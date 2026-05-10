import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from sqlalchemy import text

from app.core.config import settings
from app.db.base import async_session_factory, engine
from app.db.importer import run_import
from app.db import models
from app.routers import auth, auction, health, recipes, items
from app.services.stalcraft_client import StalcraftClient
from app.services.db_updater import ensure_repo, watch_for_updates
from app.services.price_collector import PriceCollector, populate_craft_items
from fastapi.staticfiles import StaticFiles
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_schema_migrations() -> None:
    """Применяет ADD COLUMN IF NOT EXISTS для колонок, добавленных после первого деплоя.
    create_all создаёт только отсутствующие таблицы — существующие он не трогает.
    Этот шаг закрывает разрыв без полноценного Alembic.
    """
    migrations = [
        # craft_items: колонки добавлены в v2
        "ALTER TABLE craft_items ADD COLUMN IF NOT EXISTS auction_available BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE craft_items ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ",
        # item_request_stats: создана в v2 (create_all покроет, но безопаснее явно)
        # Здесь можно добавлять новые ALTER TABLE по мере роста схемы
    ]
    async with engine.begin() as conn:
        for sql in migrations:
            await conn.execute(text(sql))
            logger.debug("Migration applied: %s", sql[:60])
    logger.info("Schema migrations done (%d statements)", len(migrations))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Клонирование репозитория и подключение иконок
    ensure_repo()

    icons_path = Path(settings.stalcraft_db_path) / settings.stalcraft_region / "icons"
    if icons_path.exists():
        app.mount("/icons", StaticFiles(directory=str(icons_path)), name="icons")
    else:
        logger.warning("icons path not found after ensure_repo: %s", icons_path)

    # 2. Создать таблицы + добавить новые колонки в существующие
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    await run_schema_migrations()
    logger.info("DB schema up to date")

    # 3. Импорт данных из stalcraft-database
    async with async_session_factory() as session:
        await run_import(session, region=settings.stalcraft_region)

    # 4. Заполнить таблицу craft_items (нужна коллектору для приоритизации)
    async with async_session_factory() as session:
        await populate_craft_items(session, region=settings.stalcraft_region)

    # 5. Фоновый мониторинг git-репозитория
    watcher_task = asyncio.create_task(watch_for_updates())
    logger.info("DB watcher started")

    # 6. Фоновый коллектор цен — ЕДИНСТВЕННЫЙ компонент с доступом к Stalcraft API
    collector = PriceCollector(region=settings.stalcraft_region)
    collector_task = asyncio.create_task(collector.start())
    logger.info("PriceCollector started")

    # StalcraftClient для обратной совместимости (роутеры auction/auth могут его использовать)
    app.state.stalcraft_client = StalcraftClient()

    try:
        yield
    finally:
        logger.info("Shutting down...")
        watcher_task.cancel()
        collector_task.cancel()
        await collector.stop()
        await app.state.stalcraft_client.aclose()
        await engine.dispose()
        logger.info("Shutdown complete")


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
