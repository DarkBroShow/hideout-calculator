from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AdditionalLotInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    lot_id: str
    seller_id: str
    # Добавляй поля по мере необходимости


class PriceEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    amount: int = Field(..., ge=1)
    price: int = Field(..., ge=0)
    time: datetime = Field(..., description="Время продажи")
    additional: Dict[str, Any] = Field(
        default={}, 
        description="Доп. данные (lot_id, seller_id при additional=true)"
    )


class AuctionHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total: int = Field(..., ge=0)
    prices: List[PriceEntry] = Field(..., min_items=0, max_items=200)


class AuctionHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    region: str
    limit: int
    offset: int
    additional: bool
    history: AuctionHistory

class AuctionLot(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    item_id: str = Field(..., alias="itemId")
    amount: int = Field(..., ge=1)
    start_price: int = Field(..., alias="startPrice", ge=0)
    current_price: Optional[int] = Field(None, alias="currentPrice", ge=0)
    buyout_price: int = Field(..., alias="buyoutPrice", ge=0)
    start_time: datetime = Field(..., alias="startTime")
    end_time: datetime = Field(..., alias="endTime")
    additional: Dict[str, Any] = Field(default={})


class AuctionLotsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    region: str
    limit: int
    offset: int
    additional: bool
    total: int
    lots: List[AuctionLot]