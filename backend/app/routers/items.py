from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from app.db.base import async_session_factory
from app.db.models import Item

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/search")
async def search_items(q: str = Query(..., min_length=1)):
    async with async_session_factory() as session:
        pattern = f"%{q}%"
        result = await session.execute(
            select(Item)
            .where(
                or_(
                    Item.name_ru.ilike(pattern),
                    Item.name_en.ilike(pattern),
                    Item.id.ilike(pattern),
                )
            )
            .limit(50)
        )
        items = result.scalars().all()

    return [
        {
            "id": item.id,
            "category": item.category,
            "name_ru": item.name_ru,
            "name_en": item.name_en,
            "icon_path": item.icon_path,
            "color": item.color,
        }
        for item in items
    ]