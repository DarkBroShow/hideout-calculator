import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

# При 429 / 401 принудительно сбрасываем токен и делаем одну переэмиссию.
_RETRYABLE_STATUSES = {401, 429}


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
        return datetime.now(timezone.utc) < (self._token_expires_at - timedelta(minutes=5))

    async def _fetch_access_token(self) -> tuple[str, datetime]:
        logger.info("Fetching new STALCRAFT access token")
        response = await self._client.post(
            settings.stalcraft_oauth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.stalcraft_client_id,
                "client_secret": settings.stalcraft_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
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
            return self._token  # type: ignore[return-value]
        async with self._token_lock:
            if self._token_is_valid():
                return self._token  # type: ignore[return-value]
            token, expires_at = await self._fetch_access_token()
            self._token = token
            self._token_expires_at = expires_at
            return token

    def _invalidate_token(self) -> None:
        """Сбросить кешированный токен — следующий запрос получит новый."""
        self._token = None
        self._token_expires_at = None

    async def _get(self, url: str, params: dict, max_retries: int = 5) -> dict:
        """GET с автоматическим обновлением токена при 429/401.
        Каждый раз при ошибке сбрасывает токен и получает новый.
        """
        response = None
        for attempt in range(max_retries):
            token = await self.get_access_token()
            response = await self._client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code in _RETRYABLE_STATUSES:
                logger.warning(
                    "STALCRAFT API returned %s (attempt %d/%d) — rotating token",
                    response.status_code,
                    attempt + 1,
                    max_retries,
                )
                self._invalidate_token()
                continue
            response.raise_for_status()
            return response.json()
        # Все попытки исчерпаны — бросаем ошибку последнего ответа
        if response is not None:
            response.raise_for_status()
        raise RuntimeError("STALCRAFT API unreachable after %d attempts" % max_retries)

    async def get_item_price_history(
        self,
        item_id: str,
        region: str = "ru",
        limit: int = 20,
        offset: int = 0,
        additional: bool = False,
    ) -> dict:
        region_value = (region or settings.stalcraft_region).lower()
        params: dict = {"limit": limit, "offset": offset}
        if additional:
            params["additional"] = "true"
        url = f"{settings.stalcraft_api_base_url}/{region_value}/auction/{item_id}/history"
        return await self._get(url, params)

    async def get_item_lots(
        self,
        item_id: str,
        region: str = "ru",
        limit: int = 20,
        offset: int = 0,
        additional: bool = False,
        sort: str = "time_created",
        order: str = "desc",
    ) -> dict:
        region_value = (region or settings.stalcraft_region).lower()
        params: dict = {
            "limit": limit,
            "offset": offset,
            "additional": str(additional).lower(),
            "sort": sort,
            "order": order,
        }
        url = f"{settings.stalcraft_api_base_url}/{region_value}/auction/{item_id}/lots"
        return await self._get(url, params)
