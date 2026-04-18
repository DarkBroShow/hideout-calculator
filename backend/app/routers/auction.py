import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.schemas.stalcraft import AuctionHistory, AuctionHistoryResponse, AuctionLotsResponse
from typing import Literal
from app.schemas.stalcraft import AuctionHistory, AuctionHistoryResponse
from app.services.stalcraft_client import StalcraftClient


router = APIRouter(prefix="/auction", tags=["auction"])


def get_stalcraft_client(request: Request) -> StalcraftClient:
    return request.app.state.stalcraft_client


@router.get("/history", response_model=AuctionHistoryResponse)
async def auction_history(
    item_id: str = Query(..., description="STALCRAFT item id"),
    region: str = Query("ru", description="Region"),
    limit: int = Query(20, ge=0, le=200, description="Max records (0-200)"),
    offset: int = Query(0, ge=0, description="Skip records"),
    additional: bool = Query(False, description="Include lot details"),
    stalcraft_client: StalcraftClient = Depends(get_stalcraft_client),
):
    try:
        raw_data = await stalcraft_client.get_item_price_history(
            item_id=item_id,
            region=region,
            limit=limit,
            offset=offset,
            additional=additional,
        )
        return AuctionHistoryResponse(
            item_id=item_id,
            region=region,
            limit=limit,
            offset=offset,
            additional=additional,
            history=AuctionHistory(**raw_data),
        )
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


@router.get("/lots", response_model=AuctionLotsResponse)
async def auction_lots(
    item_id: str = Query(..., description="STALCRAFT item id"),
    region: str = Query("ru", description="Region"),
    limit: int = Query(20, ge=0, le=200, description="Max records (0-200)"),
    offset: int = Query(0, ge=0, description="Skip records"),
    additional: bool = Query(False, description="Include lot details"),
    sort: Literal["time_created", "time_left", "current_price", "buyout_price"] = Query(
        "time_created", description="Property to sort by"
    ),
    order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    stalcraft_client: StalcraftClient = Depends(get_stalcraft_client),
):
    try:
        raw_data = await stalcraft_client.get_item_lots(
            item_id=item_id,
            region=region,
            limit=limit,
            offset=offset,
            additional=additional,
            sort=sort,
            order=order,
        )
        return AuctionLotsResponse(
            item_id=item_id,
            region=region,
            limit=limit,
            offset=offset,
            additional=additional,
            total=raw_data["total"],
            lots=raw_data["lots"],
        )
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