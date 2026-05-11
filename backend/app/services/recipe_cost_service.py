"""
recipe_cost_service.py — Расчёт оптимальной стоимости крафта/покупки.

Цены берутся ТОЛЬКО из БД (item_price_cache).
Все обращения к Stalcraft API — через фоновый PriceCollector.

При каждом запросе фиксируем статистику в item_request_stats:
все участвующие предметы (корень + все ингредиенты рекурсивно).
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item, Recipe, RecipeIngredient, ItemPriceCache, ItemRequestStats
from app.core.game_config import ENERGY_SOURCES, AUCTION_COMMISSION
from app.services.price_service import get_fair_price
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

    # Только для корневой ноды — данные выбранного рецепта
    result_amount: int = 1           # сколько штук производит один крафт
    crafts_needed: int = 1           # сколько крафтов нужно для amount_needed

    components: list["NodeCost"] = field(default_factory=list)


@dataclass
class RecipeCostResult:
    item_id: str
    amount: int
    total_buy_cost: int | None          # купить итоговый предмет на аукционе
    total_craft_cost: int | None        # оптимальный крафт (per-unit × amount)
    total_materials_cost: int | None    # фактическая сумма закупки ингредиентов
    total_energy_cost: int | None       # суммарные расходы на энергию в рублях
    margin: int | None                  # реальная прибыль с батча (batch_revenue − batch_cost)
    sell_price: int | None              # цена продажи 1 шт после комиссии
    batch_revenue: int | None           # выручка от продажи всех items_produced после комиссии
    result_amount: int                  # штук за 1 крафт
    items_produced: int                 # всего будет произведено (crafts_needed × result_amount)
    is_profitable: bool
    profitable_reason: str | None       # почему рентабелен/нет
    energy_price_per_unit: int | None   # цена 1 единицы энергии
    components_summary: list[dict]      # итоговый список всех ресурсов (плоский)
    tree: NodeCost


# ---------------------------------------------------------------------------
# Трекинг запросов
# ---------------------------------------------------------------------------

async def _track_requests(
    item_ids: set[str],
    region: str,
    session: AsyncSession,
) -> None:
    """Атомарно увеличивает счётчик запросов для каждого item_id.
    Используется коллектором для приоритизации обновлений цен.
    """
    if not item_ids:
        return

    now = datetime.now(timezone.utc)
    rows = [
        {"item_id": iid, "region": region, "request_count": 1, "last_requested_at": now}
        for iid in item_ids
    ]
    stmt = pg_insert(ItemRequestStats).values(rows).on_conflict_do_update(
        index_elements=["item_id", "region"],
        set_={
            "request_count": ItemRequestStats.request_count + 1,
            "last_requested_at": now,
        },
    )
    await session.execute(stmt)
    logger.debug("Tracked request for %d items in region %s", len(item_ids), region)


def _collect_item_ids(node: "NodeCost", result: set[str] | None = None) -> set[str]:
    """Рекурсивно собирает все item_id из дерева стоимости."""
    if result is None:
        result = set()
    result.add(node.item_id)
    for child in node.components:
        _collect_item_ids(child, result)
    return result


# ---------------------------------------------------------------------------
# Цена энергии
# ---------------------------------------------------------------------------

async def _get_energy_price(
    session: AsyncSession,
    region: str,
) -> float | None:
    """Цена 1 единицы энергии = min по всем источникам (из кэша БД)."""
    best: float | None = None
    for item_id, energy_per_unit in ENERGY_SOURCES.items():
        cache = await get_fair_price(item_id, session, region)
        if cache and cache.fair_price:
            price_per_energy = cache.fair_price / energy_per_unit
            if best is None or price_per_energy < best:
                best = price_per_energy
    if best is not None:
        logger.debug("Energy price: %.4f ₽/ед", best)
    else:
        logger.debug("Energy price: no data (energy source prices not available)")
    return best


# ---------------------------------------------------------------------------
# Рекурсивное построение дерева стоимости
# ---------------------------------------------------------------------------

async def _build_node(
    item_id: str,
    amount_needed: int,
    session: AsyncSession,
    region: str,
    energy_price: float | None,
    depth: int = 0,
    max_depth: int = 6,
    _visited: set | None = None,
    recipe_choices: dict[str, int] | None = None,
    decision_overrides: dict[str, str] | None = None,
    excluded_items: set[str] | None = None,
) -> NodeCost:
    if _visited is None:
        _visited = set()

    item = await session.get(Item, item_id)
    item_name = item.name_ru if item else item_id

    # Цена из кэша БД (без API)
    price_cache = await get_fair_price(item_id, session, region)
    auction_price = price_cache.buy_price if price_cache else None

    if auction_price is None:
        logger.debug("No auction price for %s (cache miss or stale)", item_id)

    # Предмет исключён пользователем из дерева → трактуем как "купить" (лист)
    if excluded_items and item_id in excluded_items:
        decision = "buy" if auction_price is not None else "no_data"
        logger.debug("Node %s: excluded by user, forced buy", item_id)
        return NodeCost(
            item_id=item_id,
            item_name=item_name,
            amount_needed=amount_needed,
            auction_price=auction_price,
            craft_cost=None,
            optimal_cost=auction_price,
            decision=decision,
            energy_cost=None,
            components=[],
        )

    # Принудительная покупка
    if decision_overrides and decision_overrides.get(item_id) == "buy":
        decision = "buy" if auction_price is not None else "no_data"
        logger.debug(
            "Node %s: forced buy, auction_price=%s",
            item_id, auction_price,
        )
        return NodeCost(
            item_id=item_id,
            item_name=item_name,
            amount_needed=amount_needed,
            auction_price=auction_price,
            craft_cost=None,
            optimal_cost=auction_price,
            decision=decision,
            energy_cost=None,
            components=[],
        )

    craft_cost: int | None = None
    best_components: list[NodeCost] = []
    energy_cost_total: int | None = None
    best_result_amount: int = 1
    best_crafts_needed: int = 1

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

        if recipe_choices and item_id in recipe_choices:
            forced_id = recipe_choices[item_id]
            recipes = [r for r in recipes if r.id == forced_id]

        best_recipe_cost: int | None = None

        for recipe in recipes:
            ingredients = (
                await session.execute(
                    select(RecipeIngredient).where(
                        RecipeIngredient.recipe_id == recipe.id
                    )
                )
            ).scalars().all()

            crafts_needed = -(-amount_needed // recipe.result_amount)
            leftover = crafts_needed * recipe.result_amount - amount_needed

            recipe_component_cost = 0
            recipe_components: list[NodeCost] = []
            ok = True

            for ing in ingredients:
                child = await _build_node(
                    item_id=ing.item_id,
                    amount_needed=ing.amount * crafts_needed,
                    session=session,
                    region=region,
                    energy_price=energy_price,
                    depth=depth + 1,
                    max_depth=max_depth,
                    _visited=_visited,
                    recipe_choices=recipe_choices,
                    decision_overrides=decision_overrides,
                    excluded_items=excluded_items,
                )
                recipe_components.append(child)
                if child.optimal_cost is None:
                    ok = False
                    break
                recipe_component_cost += child.optimal_cost * child.amount_needed

            if not ok:
                continue

            energy_for_recipe: int | None = None
            if energy_price and recipe.energy:
                energy_for_recipe = int(recipe.energy * crafts_needed * energy_price)
                recipe_component_cost += energy_for_recipe

            cost_per_unit = recipe_component_cost // (crafts_needed * recipe.result_amount)

            if best_recipe_cost is None or cost_per_unit < best_recipe_cost:
                best_recipe_cost = cost_per_unit
                best_components = recipe_components
                energy_cost_total = energy_for_recipe
                best_result_amount = recipe.result_amount
                best_crafts_needed = crafts_needed

        craft_cost = best_recipe_cost

    # Принятие решения
    forced = decision_overrides.get(item_id) if decision_overrides else None

    if forced == "craft" and craft_cost is not None:
        decision = "craft"
        optimal_cost = craft_cost
    elif auction_price is not None and craft_cost is not None:
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

    logger.debug(
        "Node %s (depth=%d): decision=%s, auction=%s, craft=%s, optimal=%s",
        item_id, depth, decision, auction_price, craft_cost, optimal_cost,
    )

    return NodeCost(
        item_id=item_id,
        item_name=item_name,
        amount_needed=amount_needed,
        auction_price=auction_price,
        craft_cost=craft_cost,
        optimal_cost=optimal_cost,
        decision=decision,
        energy_cost=energy_cost_total,
        result_amount=best_result_amount,
        crafts_needed=best_crafts_needed,
        components=best_components if decision == "craft" else [],
    )


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

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


def _sum_energy_cost(node: NodeCost) -> int:
    """Суммарная стоимость энергии по всему дереву (рекурсивно)."""
    return (node.energy_cost or 0) + sum(_sum_energy_cost(c) for c in node.components)


# ---------------------------------------------------------------------------
# Главная функция
# ---------------------------------------------------------------------------

async def calculate_recipe_cost(
    item_id: str,
    amount: int,
    session: AsyncSession,
    region: str | None = None,
    recipe_choices: dict[str, int] | None = None,
    decision_overrides: dict[str, str] | None = None,
    excluded_items: set[str] | None = None,
) -> RecipeCostResult:
    region = region or settings.stalcraft_region

    logger.info(
        "calculate_recipe_cost: item=%s amount=%d region=%s excluded=%s",
        item_id, amount, region, excluded_items,
    )

    energy_price = await _get_energy_price(session, region)

    tree = await _build_node(
        item_id=item_id,
        amount_needed=amount,
        session=session,
        region=region,
        energy_price=energy_price,
        recipe_choices=recipe_choices,
        decision_overrides=decision_overrides,
        excluded_items=excluded_items,
    )

    # Трекинг всех предметов в дереве
    all_item_ids = _collect_item_ids(tree)
    try:
        await _track_requests(all_item_ids, region, session)
        await session.commit()
    except Exception:
        logger.exception("Failed to track request stats (non-fatal)")

    # Цена продажи 1 шт (из кэша, без API)
    sell_price_cache = await get_fair_price(item_id, session, region)
    sell_price_raw = sell_price_cache.sell_price if sell_price_cache else None
    sell_price = int(sell_price_raw * (1 - AUCTION_COMMISSION)) if sell_price_raw else None

    total_craft_cost = (tree.craft_cost or 0) * amount if tree.craft_cost else None
    total_buy_cost = (tree.auction_price or 0) * amount if tree.auction_price else None

    flat = _flatten_components(tree)
    total_materials_cost = sum(c["total_price"] for c in flat.values()) or None
    total_energy_cost = _sum_energy_cost(tree) or None

    result_amount = tree.result_amount
    crafts_needed = tree.crafts_needed
    items_produced = crafts_needed * result_amount

    can_craft = tree.decision == "craft" and total_materials_cost is not None

    batch_revenue = (sell_price * items_produced) if (sell_price and can_craft) else None
    batch_cost = (total_materials_cost or 0) + (total_energy_cost or 0)
    margin = (batch_revenue - batch_cost) if batch_revenue is not None else None
    is_profitable = bool(margin is not None and margin > 0)

    if not can_craft:
        profitable_reason = "Рецепт крафта не найден"
    elif not is_profitable:
        if batch_revenue is not None:
            profitable_reason = "Крафт не окупается: расходы превышают выручку"
        else:
            profitable_reason = "Нет данных о ценах для расчёта"
    elif tree.craft_cost and tree.auction_price and tree.craft_cost < tree.auction_price:
        profitable_reason = "Крафт дешевле покупки"
    else:
        profitable_reason = "Крафт выгоден для перепродажи"

    logger.info(
        "calculate_recipe_cost result: item=%s decision=%s margin=%s profitable=%s",
        item_id, tree.decision, margin, is_profitable,
    )

    return RecipeCostResult(
        item_id=item_id,
        amount=amount,
        total_buy_cost=total_buy_cost,
        total_craft_cost=total_craft_cost,
        total_materials_cost=total_materials_cost,
        total_energy_cost=total_energy_cost,
        margin=margin,
        sell_price=sell_price,
        batch_revenue=batch_revenue,
        result_amount=result_amount,
        items_produced=items_produced,
        is_profitable=is_profitable,
        profitable_reason=profitable_reason,
        energy_price_per_unit=int(energy_price) if energy_price else None,
        components_summary=list(flat.values()),
        tree=tree,
    )
