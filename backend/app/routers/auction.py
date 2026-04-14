import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.stalcraft import get_item_price_history

router = APIRouter(prefix="/auction", tags=["auction"])


@router.get("/history")
async def auction_history(
    item_id: str = Query(..., description="STALCRAFT item id"),
    region: str = Query("ru", description="Region, for example ru"),
):
    try:
        data = await get_item_price_history(item_id=item_id, region=region)
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