from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hideout Backend"
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    app_debug: bool = True

    database_url: str = "postgres://hideout:hideout@hideout-db:5432/hideout"

    oauth_redirect_uri: str = "http://localhost:8080/auth/callback"
    stalcraft_client_id: str | None = None
    stalcraft_client_secret: str | None = None
    stalcraft_region: str = "ru"

    stalcraft_oauth_url: str = "https://exbo.net/oauth/token"
    stalcraft_api_base_url: str = "https://eapi.stalcraft.net"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()