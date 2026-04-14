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