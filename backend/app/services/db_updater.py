import asyncio
import logging
import subprocess
from pathlib import Path

from app.core.config import settings
from app.db.base import async_session_factory, engine
from app.db.importer import run_import
from app.db import models

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 10 * 60


class DbUpdateState:
    maintenance: bool = False
    last_commit: str | None = None


state = DbUpdateState()


def _git(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def _db_path() -> Path:
    return Path(settings.stalcraft_db_path)


def ensure_repo() -> None:
    """Клонирует репо при старте если его нет."""
    path = _db_path()
    if path.exists() and (path / ".git").exists():
        logger.info("stalcraft-database already exists, skipping clone")
        state.last_commit = _current_commit()
        return

    logger.info("Cloning stalcraft-database...")
    path.parent.mkdir(parents=True, exist_ok=True)
    result = _git([
        "clone",
        "--depth=1",
        settings.stalcraft_db_repo,
        str(path),
    ])
    if result.returncode != 0:
        raise RuntimeError(f"git clone failed: {result.stderr}")

    state.last_commit = _current_commit()
    logger.info("Cloned, commit: %s", state.last_commit)


def _current_commit() -> str:
    return _git(["rev-parse", "HEAD"], cwd=_db_path()).stdout.strip()


def _has_updates() -> bool:
    _git(["fetch"], cwd=_db_path())
    local = _git(["rev-parse", "HEAD"], cwd=_db_path()).stdout.strip()
    remote = _git(["rev-parse", "@{u}"], cwd=_db_path()).stdout.strip()
    return local != remote


def _pull() -> None:
    result = _git(["pull"], cwd=_db_path())
    logger.info("git pull: %s", result.stdout.strip())


async def _run_reimport() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    async with async_session_factory() as session:
        await run_import(session, region=settings.stalcraft_region)


async def watch_for_updates() -> None:
    while True:
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        try:
            if not _has_updates():
                logger.debug("No stalcraft-database updates found")
                continue

            logger.info("Update found, entering maintenance mode")
            state.maintenance = True

            logger.info("Waiting 5 minutes before reimport...")
            await asyncio.sleep(5 * 60)

            _pull()
            state.last_commit = _current_commit()
            logger.info("Pulled commit: %s", state.last_commit)

            await _run_reimport()
            logger.info("Reimport complete")

        except Exception:
            logger.exception("Error in db update watcher")
        finally:
            state.maintenance = False