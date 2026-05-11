import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.db.base import async_session_factory
from app.services.recipe_cost_service import calculate_recipe_cost, NodeCost, RecipeCostResult
from app.core.config import settings
from app.db.models import Item

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["recipes"])


# ---------------------------------------------------------------------------
# Pydantic-схемы
# ---------------------------------------------------------------------------

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
    total_materials_cost: int | None
    total_energy_cost: int | None
    margin: int | None
    sell_price: int | None
    batch_revenue: int | None
    result_amount: int
    items_produced: int
    is_profitable: bool
    profitable_reason: str | None
    energy_price_per_unit: int | None
    components_summary: list[dict]
    tree: NodeCostSchema


# ---------------------------------------------------------------------------
# Роуты
# ---------------------------------------------------------------------------

@router.get("/cost", response_model=RecipeCostResponse)
async def recipe_cost(
    item_id: str = Query(..., description="ID предмета"),
    amount: int = Query(1, ge=1, le=1000, description="Количество"),
    region: str = Query(None, description="Регион (по умолчанию из конфига)"),
    force_refresh: bool = Query(
        False,
        description="Устарело: цены обновляет фоновый коллектор, параметр игнорируется",
    ),
    recipe_choices: str | None = Query(
        None,
        description='JSON объект {item_id: recipe_id}, фиксирующий выбранные рецепты',
    ),
    decision_overrides: str | None = Query(
        None,
        description='JSON объект {item_id: "buy"|"craft"}, принудительное решение',
    ),
    excluded_items: str | None = Query(
        None,
        description='JSON массив [item_id, ...] — предметы исключены из дерева пользователем, '
                    'трактуются как "купить"',
    ),
):
    if force_refresh:
        logger.info(
            "/recipes/cost: force_refresh=true ignored — prices managed by PriceCollector"
        )

    choices: dict[str, int] | None = None
    if recipe_choices:
        try:
            parsed = json.loads(recipe_choices)
            if not isinstance(parsed, dict):
                raise ValueError("recipe_choices must be a JSON object")
            choices = {str(k): int(v) for k, v in parsed.items()}
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid recipe_choices: {e}")

    overrides: dict[str, str] | None = None
    if decision_overrides:
        try:
            parsed = json.loads(decision_overrides)
            if not isinstance(parsed, dict):
                raise ValueError("decision_overrides must be a JSON object")
            overrides = {str(k): str(v) for k, v in parsed.items()}
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid decision_overrides: {e}")

    excluded: set[str] | None = None
    if excluded_items:
        try:
            parsed = json.loads(excluded_items)
            if not isinstance(parsed, list):
                raise ValueError("excluded_items must be a JSON array")
            excluded = {str(v) for v in parsed}
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid excluded_items: {e}")

    async with async_session_factory() as session:
        try:
            result = await calculate_recipe_cost(
                item_id=item_id,
                amount=amount,
                session=session,
                region=region,
                recipe_choices=choices,
                decision_overrides=overrides,
                excluded_items=excluded,
            )
        except Exception as e:
            logger.exception("recipe_cost failed for item=%s", item_id)
            raise HTTPException(status_code=500, detail=str(e))

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
    force_refresh: bool = Query(
        False,
        description="Устарело: цены обновляет фоновый коллектор, параметр игнорируется",
    ),
):
    """Быстрый эндпоинт — цена одного предмета из кэша БД."""
    from app.services.price_service import get_fair_price
    if force_refresh:
        logger.info(
            "/recipes/price/%s: force_refresh=true ignored — prices managed by PriceCollector",
            item_id,
        )
    async with async_session_factory() as session:
        cache = await get_fair_price(
            item_id, session,
            region=region or settings.stalcraft_region,
        )
    if not cache:
        raise HTTPException(
            status_code=404,
            detail="Price not available — collector has not yet fetched this item",
        )
    return {
        "item_id": item_id,
        "buy_price": cache.buy_price,
        "sell_price": cache.sell_price,
        "fair_price": cache.buy_price,
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

            item = await session.get(Item, iid)

            def item_dict():
                if item:
                    return {
                        "id": item.id,
                        "name_ru": item.name_ru,
                        "name_en": item.name_en,
                        "icon_path": item.icon_path,
                        "category": item.category,
                        "color": item.color,
                    }
                return {"id": iid}

            if depth > 6 or iid in visited:
                return {"item_id": iid, "item": item_dict(), "recipes": []}
            visited = visited | {iid}
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
                "item": item_dict(),
                "recipes": recipes_out,
            }

        tree = await build_node(item_id)

    return tree
