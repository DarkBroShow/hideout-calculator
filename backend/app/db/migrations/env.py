import asyncio
import os
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from alembic import context
from app.db.base import Base
from app.db import models  # noqa: F401

config = context.config
fileConfig(config.config_file_name)

# Собираем URL из переменных окружения
def get_database_url() -> str:
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ["POSTGRES_HOST"]
    port = os.environ["POSTGRES_PORT"]
    db = os.environ["POSTGRES_DB"]
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

config.set_main_option("sqlalchemy.url", get_database_url())

target_metadata = Base.metadata