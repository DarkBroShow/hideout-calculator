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
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))