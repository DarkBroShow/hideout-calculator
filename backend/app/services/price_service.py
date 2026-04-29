import logging
import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.core.config import settings
from app.core.game_config import AUCTION_COMMISSION, ENERGY_SOURCES, TTL_TIERS
from app.db.models import AuctionPriceHistory, ItemPriceCache
from app.services.stalcraft_client import StalcraftClient

logger = logging.getLogger(__name__)


def _calc_ttl(sales_per_day: float) -> int:
    """Адаптивный TTL в секундах — пороги берутся из game_config.TTL_TIERS."""
    for min_sales, ttl in TTL_TIERS:
        if sales_per_day >= min_sales:
            return ttl
    return TTL_TIERS[-1][1]


def _weighted_median(prices: list[int], amounts: list[int]) -> int:
    """Взвешенная медиана по количеству проданных единиц."""
    pairs = sorted(zip(prices, amounts), key=lambda x: x[0])
    total = sum(a for _, a in pairs)
    target = total / 2
    cumulative = 0
    for price, amount in pairs:
        cumulative += amount
        if cumulative >= target:
            return price
    return pairs[-1][0]

def _calc_percentile(prices: list[int], p: float) -> int:
    """p от 0.0 до 1.0"""
    if not prices:
        return 0
    sorted_p = sorted(prices)
    idx = int(len(sorted_p) * p)
    return sorted_p[min(idx, len(sorted_p) - 1)]


def _fair_price_from_history(rows: list[AuctionPriceHistory]) -> dict:
    if not rows:
        return {}

    # Для sell_price — одиночные продажи из истории (amount=1)
    single_sales = [r for r in rows if r.amount == 1]
    all_prices = sorted(r.price for r in rows)

    # Если одиночных мало — используем все
    sell_source = single_sales if len(single_sales) >= 10 else rows
    sell_prices = sorted(r.price for r in sell_source)

    # p60 одиночных — реалистичная цена по которой купят у тебя
    sell_idx = int(len(sell_prices) * 0.60)
    sell_price_before_tax = sell_prices[min(sell_idx, len(sell_prices) - 1)]
    sell_price = int(sell_price_before_tax * (1 - AUCTION_COMMISSION))

    # buy_price временный (перезапишется из лотов)
    buy_idx = int(len(all_prices) * 0.25)
    buy_price = all_prices[min(buy_idx, len(all_prices) - 1)]

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    recent = [r for r in rows if r.sold_at >= day_ago]
    sales_per_day = float(len(recent))

    return {
        "buy_price": buy_price,
        "sell_price": sell_price,
        "fair_price": buy_price,
        "min_price": all_prices[0],
        "max_price": all_prices[-1],
        "sales_per_day": sales_per_day,
        "sample_size": len(rows),
        "ttl_seconds": _calc_ttl(sales_per_day),
    }

async def get_buy_price_from_lots(
    item_id: str,
    stalcraft: StalcraftClient,
    region: str,
) -> int | None:
    """
    Реальная цена закупки — минимальная цена за штуку из активных лотов.
    Сначала ищем одиночные лоты, затем массовые.
    """
    try:
        raw = await stalcraft.get_item_lots(
            item_id=item_id,
            region=region,
            limit=50,
            offset=0,
            sort="current_price",
            order="asc",
        )
    except Exception:
        logger.exception("Failed to fetch lots for %s", item_id)
        return None

    lots = raw.get("lots", [])
    if not lots:
        return None

    # Разделяем одиночные и массовые лоты
    single_lots = [l for l in lots if l.get("amount", 1) == 1]
    bulk_lots = [l for l in lots if l.get("amount", 1) > 1]

    # Цена за штуку для каждого лота
    def price_per_unit(lot: dict) -> int:
        buyout = lot.get("buyoutPrice") or lot.get("currentPrice") or 0
        amount = lot.get("amount", 1)
        return buyout // amount if amount > 0 else buyout

    # Приоритет: одиночные лоты — самые честные цены
    if single_lots:
        # Берём медиану одиночных (не минимум — он может быть выбросом)
        prices = sorted(price_per_unit(l) for l in single_lots)
        # p25 одиночных — "реалистичная дешёвая цена"
        idx = max(0, int(len(prices) * 0.25))
        return prices[idx]

    # Нет одиночных — берём минимальную цену за штуку среди массовых
    if bulk_lots:
        prices = sorted(price_per_unit(l) for l in bulk_lots)
        return prices[0]

    return None

async def get_fair_price(
    item_id: str,
    session: AsyncSession,
    stalcraft: StalcraftClient,
    region: str | None = None,
    force_refresh: bool = False,
) -> ItemPriceCache | None:
    region = region or settings.stalcraft_region
    now = datetime.now(timezone.utc)

    if not force_refresh:
        cache_row = await session.get(ItemPriceCache, (item_id, region))
        if cache_row:
            expires_at = cache_row.updated_at + timedelta(seconds=cache_row.ttl_seconds)
            if now < expires_at:
                return cache_row

    # Тянем историю для sell_price и метрик ликвидности
    try:
        raw = await stalcraft.get_item_price_history(
            item_id=item_id, region=region, limit=200, offset=0,
        )
    except Exception:
        logger.exception("Failed to fetch history for %s", item_id)
        return await session.get(ItemPriceCache, (item_id, region))

    price_entries = raw.get("prices", [])
    for entry in price_entries:
        amount = entry["amount"]
        price_per_unit = entry["price"] // amount if amount > 0 else entry["price"]
        stmt = pg_insert(AuctionPriceHistory).values(
            item_id=item_id,
            region=region,
            amount=amount,
            price=price_per_unit,
            sold_at=datetime.fromisoformat(entry["time"].replace("Z", "+00:00")),
            fetched_at=now,
        ).on_conflict_do_nothing(constraint="uq_auction_history")
        await session.execute(stmt)

    history_rows = (
        await session.execute(
            select(AuctionPriceHistory)
            .where(
                AuctionPriceHistory.item_id == item_id,
                AuctionPriceHistory.region == region,
            )
            .order_by(AuctionPriceHistory.sold_at.desc())
            .limit(500)
        )
    ).scalars().all()

    agg = _fair_price_from_history(list(history_rows))
    if not agg:
        return None

    # Цена закупки — из активных лотов (реальный рынок прямо сейчас)
    buy_price = await get_buy_price_from_lots(item_id, stalcraft, region)
    if buy_price is not None:
        agg["buy_price"] = buy_price
        agg["fair_price"] = buy_price

    cache_stmt = pg_insert(ItemPriceCache).values(
        item_id=item_id,
        region=region,
        updated_at=now,
        **agg,
    ).on_conflict_do_update(
        index_elements=["item_id", "region"],
        set_={**agg, "updated_at": now},
    )
    await session.execute(cache_stmt)
    await session.commit()

    return await session.get(ItemPriceCache, (item_id, region))