import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class StalcraftClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "HideoutCalculator/1.0"},
        )
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _token_is_valid(self) -> bool:
        if not self._token or not self._token_expires_at:
            return False

        refresh_margin = timedelta(minutes=5)
        now = datetime.now(timezone.utc)
        return now < (self._token_expires_at - refresh_margin)

    async def _fetch_access_token(self) -> tuple[str, datetime]:
        logger.info("Fetching new STALCRAFT access token")

        response = await self._client.post(
            settings.stalcraft_oauth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.stalcraft_client_id,
                "client_secret": settings.stalcraft_client_secret,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        data = response.json()

        token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        logger.info("Received STALCRAFT token; expires in %s seconds", expires_in)
        return token, expires_at

    async def get_access_token(self) -> str:
        if self._token_is_valid():
            logger.debug("Using cached STALCRAFT token")
            return self._token  # type: ignore[return-value]

        async with self._token_lock:
            if self._token_is_valid():
                logger.debug("Using cached STALCRAFT token after lock")
                return self._token  # type: ignore[return-value]

            token, expires_at = await self._fetch_access_token()
            self._token = token
            self._token_expires_at = expires_at
            return token

    async def get_item_price_history(self, item_id: str, region: str = "ru") -> dict:
        token = await self.get_access_token()
        region_value = (region or settings.stalcraft_region).lower()
        url = f"{settings.stalcraft_api_base_url}/{region_value}/auction/{item_id}/history"

        response = await self._client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        return response.json()