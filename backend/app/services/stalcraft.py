import httpx

from app.core.config import settings


async def get_app_access_token() -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
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
        return data["access_token"]


async def get_item_price_history(item_id: str, region: str | None = None) -> dict:
    token = await get_app_access_token()
    region_value = (region or settings.stalcraft_region).lower()

    url = f"{settings.stalcraft_api_base_url}/{region_value}/auction/{item_id}/history"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        return response.json()