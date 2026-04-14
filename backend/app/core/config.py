from typing import Optional

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App / Backend
    app_name: str = "Hideout Backend"
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=4000, alias="BACKEND_PORT")

    # Глобовый debug FastAPI
    app_debug: bool = True

    # Отладочные эндпоинты
    backend_debug: bool = Field(default=False, alias="BACKEND_DEBUG")

    # Database
    postgres_user: str = Field(default="hideout", alias="POSTGRES_USER")
    postgres_password: str = Field(default="hideout", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="hideout", alias="POSTGRES_DB")
    postgres_host: str = Field(default="hideout-db", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    database_url: str = "postgres://hideout:hideout@hideout-db:5432/hideout"

    # Stalcraft
    stalcraft_client_id: Optional[str] = Field(default=None, alias="STALCRAFT_CLIENT_ID")
    stalcraft_client_secret: Optional[str] = Field(default=None, alias="STALCRAFT_CLIENT_SECRET")
    stalcraft_region: str = Field(default="ru", alias="STALCRAFT_REGION")

    stalcraft_oauth_url: str = "https://exbo.net/oauth/token"
    stalcraft_api_base_url: str = "https://eapi.stalcraft.net"

    # OAuth redirect
    oauth_redirect_uri: HttpUrl = "http://localhost:4000/auth/callback"

    @field_validator("oauth_redirect_uri", mode="before")
    @classmethod
    def build_oauth_redirect_uri(cls, v, info):
        if v is not None:
            return v
        data = info.data
        host = data.get("app_host") or "localhost"
        port = data.get("app_port") or 4000
        return f"http://{host}:{port}/auth/callback"

    @field_validator("database_url", mode="before")
    @classmethod
    def build_database_url(cls, v, info):
        data = info.data

        user = data.get("postgres_user") or "hideout"
        password = data.get("postgres_password") or "hideout"
        db = data.get("postgres_db") or "hideout"
        host = data.get("postgres_host") or "hideout-db"
        port = data.get("postgres_port") or 5432

        return f"postgres://{user}:{password}@{host}:{port}/{db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()