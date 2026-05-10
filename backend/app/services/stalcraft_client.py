"""
stalcraft_client.py — HTTP-клиент для Stalcraft Auction API.

Особенности:
  • Автоматическое получение и кэширование OAuth 2.0 токена.
  • Счётчик запросов: при приближении к лимиту (TOKEN_PROACTIVE_ROTATE_AT)
    токен сбрасывается превентивно ДО того, как API начнёт возвращать 429.
  • При 429/401 — сброс токена + экспоненциальный backoff между попытками.
  • _fetch_access_token сам retry-ит с backoff если OAuth-сервер недоступен.
  • TokenExhaustedError: сигнал коллектору что нужно подождать.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Статусы, при которых принудительно ротируем токен
_RETRYABLE_STATUSES = {401, 429}

# Сколько запросов выдерживает один токен (по документации Stalcraft API)
TOKEN_MAX_REQUESTS: int = 400

# При достижении этого порога токен ротируется превентивно
TOKEN_PROACTIVE_ROTATE_AT: int = 380


class TokenExhaustedError(Exception):
    """Все попытки получить рабочий токен и выполнить запрос исчерпаны.
    Коллектор должен подождать перед следующим запросом.
    """


class StalcraftClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "HideoutCalculator/1.0"},
        )
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()

        # Счётчик запросов текущего токена
        self._request_count: int = 0

    async def aclose(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Управление токеном
    # ------------------------------------------------------------------

    def _token_is_valid(self) -> bool:
        if not self._token or not self._token_expires_at:
            return False
        if datetime.now(timezone.utc) >= (self._token_expires_at - timedelta(minutes=5)):
            return False
        # Превентивная ротация при приближении к лимиту запросов
        if self._request_count >= TOKEN_PROACTIVE_ROTATE_AT:
            logger.info(
                "Token proactive rotation: %d/%d requests used",
                self._request_count, TOKEN_MAX_REQUESTS,
            )
            return False
        return True

    async def _fetch_access_token(self) -> tuple[str, datetime]:
        """Получает новый токен у OAuth-сервера. Retry с backoff при ошибках."""
        max_oauth_retries = 5
        for attempt in range(max_oauth_retries):
            try:
                logger.info(
                    "Fetching new STALCRAFT access token (attempt %d/%d)",
                    attempt + 1, max_oauth_retries,
                )
                response = await self._client.post(
                    settings.stalcraft_oauth_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.stalcraft_client_id,
                        "client_secret": settings.stalcraft_client_secret,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code in _RETRYABLE_STATUSES:
                    wait = 2 ** attempt
                    logger.warning(
                        "OAuth server returned %s — waiting %ds before retry",
                        response.status_code, wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()
                token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                logger.info(
                    "Received STALCRAFT token; expires in %s seconds", expires_in
                )
                return token, expires_at

            except httpx.TimeoutException:
                wait = 2 ** attempt
                logger.warning(
                    "OAuth server timeout (attempt %d/%d) — waiting %ds",
                    attempt + 1, max_oauth_retries, wait,
                )
                if attempt < max_oauth_retries - 1:
                    await asyncio.sleep(wait)
                else:
                    raise

        raise TokenExhaustedError(
            f"Cannot obtain OAuth token after {max_oauth_retries} attempts"
        )

    async def get_access_token(self) -> str:
        if self._token_is_valid():
            return self._token  # type: ignore[return-value]
        async with self._token_lock:
            if self._token_is_valid():
                return self._token  # type: ignore[return-value]
            token, expires_at = await self._fetch_access_token()
            self._token = token
            self._token_expires_at = expires_at
            self._request_count = 0  # Сброс счётчика при новом токене
            logger.info("Token rotated, request counter reset")
            return token

    def _invalidate_token(self) -> None:
        """Сбросить кешированный токен — следующий запрос получит новый."""
        self._token = None
        self._token_expires_at = None
        self._request_count = 0

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    async def _get(self, url: str, params: dict, max_retries: int = 5) -> dict:
        """GET с автоматическим обновлением токена при 429/401.

        При каждой ошибке:
          • Сбрасывает токен (следующая попытка получит новый)
          • Ждёт 2^attempt секунд перед следующей попыткой

        Если все попытки исчерпаны — бросает TokenExhaustedError.
        """
        response = None
        for attempt in range(max_retries):
            try:
                token = await self.get_access_token()
            except TokenExhaustedError:
                raise
            except Exception as e:
                raise TokenExhaustedError(f"Failed to get token: {e}") from e

            response = await self._client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )

            if response.status_code in _RETRYABLE_STATUSES:
                wait = 2 ** attempt
                logger.warning(
                    "STALCRAFT API returned %s for %s (attempt %d/%d) — "
                    "rotating token, waiting %ds",
                    response.status_code, url,
                    attempt + 1, max_retries,
                    wait,
                )
                self._invalidate_token()
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait)
                continue

            # Успешный запрос — считаем
            self._request_count += 1
            response.raise_for_status()
            return response.json()

        # Все попытки исчерпаны
        logger.error(
            "STALCRAFT API unreachable after %d attempts for %s",
            max_retries, url,
        )
        raise TokenExhaustedError(
            f"API returned {response.status_code if response else '?'} "
            f"after {max_retries} attempts for {url}"
        )

    # ------------------------------------------------------------------
    # Методы API
    # ------------------------------------------------------------------

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
