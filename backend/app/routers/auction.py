import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.services.stalcraft_client import StalcraftClient


router = APIRouter(prefix="/auction", tags=["auction"])


def get_stalcraft_client(request: Request) -> StalcraftClient:
    return request.app.state.stalcraft_client


@router.get("/history")
async def auction_history(
    item_id: str = Query(..., description="STALCRAFT item id"),
    region: str = Query("ru", description="Region, for example ru"),
    stalcraft_client: StalcraftClient = Depends(get_stalcraft_client),
):
    try:
        data = await stalcraft_client.get_item_price_history(item_id=item_id, region=region)
        return {
            "item_id": item_id,
            "region": region,
            "history": data,
        }
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "upstream_http_status_error",
                "status_code": exc.response.status_code,
                "url": str(exc.request.url),
                "response_text": exc.response.text,
            },
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "upstream_http_error",
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
        )