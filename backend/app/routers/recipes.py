from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional

from app.db.base import async_session_factory
from app.services.recipe_cost_service import calculate_recipe_cost, NodeCost, RecipeCostResult
from app.services.stalcraft_client import StalcraftClient
from app.core.config import settings
from app.db.models import Item

router = APIRouter(prefix="/recipes", tags=["recipes"])


def get_stalcraft_client(request: Request) -> StalcraftClient:
    return request.app.state.stalcraft_client


# Pydantic-схемы для ответа
class NodeCostSchema(BaseModel):
    item_id: str
    item_name: str | None
    amount_needed: int
    auction_price: int | None
    craft_cost: int | None
    optimal_cost: int | None
    decision: str
    energy_cost: int | None
    components: list["NodeCostSchema"] = []

    class Config:
        from_attributes = True

NodeCostSchema.model_rebuild()


class RecipeCostResponse(BaseModel):
    item_id: str
    amount: int
    total_buy_cost: int | None
    total_craft_cost: int | None
    margin: int | None
    sell_price: int | None
    is_profitable: bool
    profitable_reason: str | None
    energy_price_per_unit: int | None
    components_summary: list[dict]
    tree: NodeCostSchema


@router.get("/cost", response_model=RecipeCostResponse)
async def recipe_cost(
    item_id: str = Query(..., description="ID предмета"),
    amount: int = Query(1, ge=1, le=1000, description="Количество"),
    region: str = Query(None, description="Регион (по умолчанию из конфига)"),
    force_refresh: bool = Query(False, description="Принудительно обновить цены"),
    stalcraft: StalcraftClient = Depends(get_stalcraft_client),
):
    async with async_session_factory() as session:
        try:
            result = await calculate_recipe_cost(
                item_id=item_id,
                amount=amount,
                session=session,
                stalcraft=stalcraft,
                region=region,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Конвертируем dataclass в dict для Pydantic
    def node_to_dict(node: NodeCost) -> dict:
        return {
            "item_id": node.item_id,
            "item_name": node.item_name,
            "amount_needed": node.amount_needed,
            "auction_price": node.auction_price,
            "craft_cost": node.craft_cost,
            "optimal_cost": node.optimal_cost,
            "decision": node.decision,
            "energy_cost": node.energy_cost,
            "components": [node_to_dict(c) for c in node.components],
        }

    return {
        **result.__dict__,
        "tree": node_to_dict(result.tree),
    }


@router.get("/price/{item_id}")
async def item_price(
    item_id: str,
    region: str = Query(None),
    force_refresh: bool = Query(False),
    stalcraft: StalcraftClient = Depends(get_stalcraft_client),
):
    """Быстрый эндпоинт — цена одного предмета."""
    from app.services.price_service import get_fair_price
    async with async_session_factory() as session:
        cache = await get_fair_price(
            item_id, session, stalcraft,
            region=region or settings.stalcraft_region,
            force_refresh=force_refresh,
        )
    if not cache:
        raise HTTPException(status_code=404, detail="Price not available")
    return {
        "item_id": item_id,
        "buy_price": cache.buy_price,
        "sell_price": cache.sell_price,
        "fair_price": cache.buy_price,  # обратная совместимость
        "min_price": cache.min_price,
        "max_price": cache.max_price,
        "sales_per_day": cache.sales_per_day,
        "sample_size": cache.sample_size,
        "updated_at": cache.updated_at,
        "ttl_seconds": cache.ttl_seconds,
    }

@router.get("/tree/{item_id}")
async def recipe_tree(item_id: str, region: str = Query(None)):
    """Структура дерева рецепта без цен — быстрый эндпоинт."""
    from sqlalchemy import select
    from app.db.models import Recipe, RecipeIngredient
    from app.db.base import async_session_factory

    region = region or settings.stalcraft_region

    async with async_session_factory() as session:
        async def build_node(iid: str, depth: int = 0, visited: set = None) -> dict:
            if visited is None:
                visited = set()
            if depth > 6 or iid in visited:
                return {"item_id": iid, "recipes": []}
            visited = visited | {iid}

            item = await session.get(Item, iid)
            recipes_rows = (await session.execute(
                select(Recipe).where(
                    Recipe.result_item_id == iid,
                    Recipe.region == region,
                )
            )).scalars().all()

            recipes_out = []
            for recipe in recipes_rows:
                ings = (await session.execute(
                    select(RecipeIngredient).where(
                        RecipeIngredient.recipe_id == recipe.id
                    )
                )).scalars().all()

                ingredients_out = []
                for ing in ings:
                    child = await build_node(ing.item_id, depth + 1, visited)
                    ingredients_out.append({
                        "item_id": ing.item_id,
                        "amount": ing.amount,
                        "node": child,
                    })

                recipes_out.append({
                    "recipe_id": recipe.id,
                    "bench": recipe.bench,
                    "energy": recipe.energy,
                    "result_amount": recipe.result_amount,
                    "required_perk_id": recipe.required_perk_id,
                    "required_perk_level": recipe.required_perk_level,
                    "category_ru": recipe.category_ru,
                    "ingredients": ingredients_out,
                })

            return {
                "item_id": iid,
                "item": {
                    "id": item.id if item else iid,
                    "name_ru": item.name_ru if item else None,
                    "name_en": item.name_en if item else None,
                    "icon_path": item.icon_path if item else None,
                    "category": item.category if item else None,
                    "color": item.color if item else None,
                } if item else {"id": iid},
                "recipes": recipes_out,
            }

        tree = await build_node(item_id)

    return tree