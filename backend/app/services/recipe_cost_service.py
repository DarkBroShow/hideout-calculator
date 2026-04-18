import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item, Recipe, RecipeIngredient, ItemPriceCache
from app.services.price_service import get_fair_price, ENERGY_SOURCES
from app.services.stalcraft_client import StalcraftClient
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NodeCost:
    item_id: str
    item_name: str | None
    amount_needed: int

    auction_price: int | None        # цена покупки на аукционе (за 1 шт)
    craft_cost: int | None           # стоимость крафта (за 1 шт)
    optimal_cost: int | None         # min(auction, craft)
    decision: str = "unknown"        # "buy" | "craft" | "no_data"

    energy_cost: int | None = None   # стоимость энергии для этого рецепта
    leftover: int = 0                # остаток если крафтим больше чем нужно

    components: list["NodeCost"] = field(default_factory=list)


@dataclass  
class RecipeCostResult:
    item_id: str
    amount: int
    total_buy_cost: int | None          # купить всё на аукционе
    total_craft_cost: int | None        # оптимальный крафт
    margin: int | None                  # продажная цена − затраты
    sell_price: int | None              # цена итогового предмета на аукционе
    is_profitable: bool
    profitable_reason: str | None       # почему рентабелен/нет
    energy_price_per_unit: int | None   # цена 1 единицы энергии
    components_summary: list[dict]      # итоговый список всех ресурсов (плоский)
    tree: NodeCost


async def _get_energy_price(
    session: AsyncSession,
    stalcraft: StalcraftClient,
    region: str,
) -> float | None:
    """Цена 1 единицы энергии = min по всем источникам."""
    best: float | None = None
    for item_id, energy_per_unit in ENERGY_SOURCES.items():
        cache = await get_fair_price(item_id, session, stalcraft, region)
        if cache and cache.fair_price:
            price_per_energy = cache.fair_price / energy_per_unit
            if best is None or price_per_energy < best:
                best = price_per_energy
    return best


async def _build_node(
    item_id: str,
    amount_needed: int,
    session: AsyncSession,
    stalcraft: StalcraftClient,
    region: str,
    energy_price: float | None,
    depth: int = 0,
    max_depth: int = 6,
    _visited: set | None = None,
) -> NodeCost:
    if _visited is None:
        _visited = set()

    # Получаем предмет
    item = await session.get(Item, item_id)
    item_name = item.name_ru if item else item_id

    # Цена на аукционе
    price_cache = await get_fair_price(item_id, session, stalcraft, region)
    auction_price = price_cache.buy_price if price_cache else None

    # Ищем лучший рецепт (если есть и не превышена глубина)
    craft_cost: int | None = None
    best_components: list[NodeCost] = []
    energy_cost_total: int | None = None

    if depth < max_depth and item_id not in _visited:
        _visited = _visited | {item_id}

        recipes = (
            await session.execute(
                select(Recipe).where(
                    Recipe.result_item_id == item_id,
                    Recipe.region == region,
                )
            )
        ).scalars().all()

        best_recipe_cost: int | None = None

        for recipe in recipes:
            ingredients = (
                await session.execute(
                    select(RecipeIngredient).where(
                        RecipeIngredient.recipe_id == recipe.id
                    )
                )
            ).scalars().all()

            # Считаем сколько крафтов нужно (с учётом result_amount)
            crafts_needed = -(-amount_needed // recipe.result_amount)  # ceil div
            leftover = crafts_needed * recipe.result_amount - amount_needed

            recipe_component_cost = 0
            recipe_components: list[NodeCost] = []
            ok = True

            for ing in ingredients:
                child = await _build_node(
                    item_id=ing.item_id,
                    amount_needed=ing.amount * crafts_needed,
                    session=session,
                    stalcraft=stalcraft,
                    region=region,
                    energy_price=energy_price,
                    depth=depth + 1,
                    max_depth=max_depth,
                    _visited=_visited,
                )
                recipe_components.append(child)
                if child.optimal_cost is None:
                    ok = False
                    break
                recipe_component_cost += child.optimal_cost * child.amount_needed

            if not ok:
                continue

            # Стоимость энергии
            energy_for_recipe: int | None = None
            if energy_price and recipe.energy:
                energy_for_recipe = int(recipe.energy * crafts_needed * energy_price)
                recipe_component_cost += energy_for_recipe

            # Себестоимость за 1 шт
            cost_per_unit = recipe_component_cost // (crafts_needed * recipe.result_amount)

            if best_recipe_cost is None or cost_per_unit < best_recipe_cost:
                best_recipe_cost = cost_per_unit
                best_components = recipe_components
                energy_cost_total = energy_for_recipe

        craft_cost = best_recipe_cost

    # Решение
    if auction_price is not None and craft_cost is not None:
        if craft_cost < auction_price:
            decision = "craft"
            optimal_cost = craft_cost
        else:
            decision = "buy"
            optimal_cost = auction_price
    elif auction_price is not None:
        decision = "buy"
        optimal_cost = auction_price
    elif craft_cost is not None:
        decision = "craft"
        optimal_cost = craft_cost
    else:
        decision = "no_data"
        optimal_cost = None

    return NodeCost(
        item_id=item_id,
        item_name=item_name,
        amount_needed=amount_needed,
        auction_price=auction_price,
        craft_cost=craft_cost,
        optimal_cost=optimal_cost,
        decision=decision,
        energy_cost=energy_cost_total,
        components=best_components if decision == "craft" else [],
    )


def _flatten_components(node: NodeCost, result: dict | None = None) -> dict:
    """Плоский список всех нужных ресурсов с суммированием."""
    if result is None:
        result = {}
    if node.decision == "buy" or not node.components:
        key = node.item_id
        if key in result:
            result[key]["amount"] += node.amount_needed
        else:
            result[key] = {
                "item_id": node.item_id,
                "item_name": node.item_name,
                "amount": node.amount_needed,
                "unit_price": node.auction_price,
                "total_price": (node.auction_price or 0) * node.amount_needed,
            }
    else:
        for child in node.components:
            _flatten_components(child, result)
    return result


async def calculate_recipe_cost(
    item_id: str,
    amount: int,
    session: AsyncSession,
    stalcraft: StalcraftClient,
    region: str | None = None,
) -> RecipeCostResult:
    region = region or settings.stalcraft_region

    energy_price = await _get_energy_price(session, stalcraft, region)

    tree = await _build_node(
        item_id=item_id,
        amount_needed=amount,
        session=session,
        stalcraft=stalcraft,
        region=region,
        energy_price=energy_price,
    )

    # Цена продажи итогового предмета
    sell_price_cache = await get_fair_price(item_id, session, stalcraft, region)
    sell_price = (sell_price_cache.sell_price or 0) * amount if sell_price_cache else None

    total_craft_cost = (tree.craft_cost or 0) * amount if tree.craft_cost else None
    total_buy_cost = (tree.auction_price or 0) * amount if tree.auction_price else None

    margin = (sell_price - total_craft_cost) if (sell_price and total_craft_cost) else None
    is_profitable = bool(margin and margin > 0)

    if not is_profitable:
        profitable_reason = "Крафт не окупается при текущих ценах"
    elif tree.craft_cost and tree.auction_price and tree.craft_cost < tree.auction_price:
        profitable_reason = "Крафт выгоднее покупки"
    else:
        profitable_reason = "Покупка выгоднее крафта"

    flat = _flatten_components(tree)

    return RecipeCostResult(
        item_id=item_id,
        amount=amount,
        total_buy_cost=total_buy_cost,
        total_craft_cost=total_craft_cost,
        margin=margin,
        sell_price=sell_price,
        is_profitable=is_profitable,
        profitable_reason=profitable_reason,
        energy_price_per_unit=int(energy_price) if energy_price else None,
        components_summary=list(flat.values()),
        tree=tree,
    )