import logging
import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AuctionPriceHistory, ItemPriceCache
from app.services.stalcraft_client import StalcraftClient

logger = logging.getLogger(__name__)

# Источники энергии: item_id → энергия за единицу
ENERGY_SOURCES = {
    "petrol_canister": 800,    # канистра с бензином — уточни реальные id
    "diesel_canister": 1000,   # канистра с дизелем
    "gas_cylinder": 1200,      # газовый баллон
}


def _calc_ttl(sales_per_day: float) -> int:
    """Адаптивный TTL в секундах в зависимости от ликвидности."""
    if sales_per_day >= 100:
        return 15 * 60          # 15 минут
    elif sales_per_day >= 10:
        return 60 * 60          # 1 час
    elif sales_per_day >= 1:
        return 6 * 60 * 60      # 6 часов
    else:
        return 24 * 60 * 60     # 24 часа


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


def _fair_price_from_history(rows: list[AuctionPriceHistory]) -> dict:
    """Считает справедливую цену из сырых данных."""
    if not rows:
        return {}

    # Отсекаем топ и боттом 10% по цене
    prices_sorted = sorted(rows, key=lambda r: r.price)
    cut = max(1, len(prices_sorted) // 10)
    trimmed = prices_sorted[cut:-cut] if len(prices_sorted) > 20 else prices_sorted

    prices = [r.price for r in trimmed]
    amounts = [r.amount for r in trimmed]

    # Продажи за сутки — смотрим диапазон дат в выборке
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    recent = [r for r in rows if r.sold_at.replace(tzinfo=timezone.utc) >= day_ago]
    sales_per_day = float(len(recent))

    return {
        "fair_price": _weighted_median(prices, amounts),
        "min_price": min(prices),
        "max_price": max(prices),
        "sales_per_day": sales_per_day,
        "sample_size": len(trimmed),
        "ttl_seconds": _calc_ttl(sales_per_day),
    }


async def get_fair_price(
    item_id: str,
    session: AsyncSession,
    stalcraft: StalcraftClient,
    region: str | None = None,
    force_refresh: bool = False,
) -> ItemPriceCache | None:
    """
    Возвращает кэшированную цену. Если TTL истёк или force_refresh — обновляет из API.
    """
    region = region or settings.stalcraft_region
    now = datetime.now(timezone.utc)

    # Проверяем кэш
    if not force_refresh:
        cache_row = await session.get(ItemPriceCache, (item_id, region))
        if cache_row:
            expires_at = cache_row.updated_at.replace(tzinfo=timezone.utc) + timedelta(
                seconds=cache_row.ttl_seconds
            )
            if now < expires_at:
                logger.debug("Price cache hit for %s (TTL ok)", item_id)
                return cache_row

    # Тянем историю из API (200 записей — максимум)
    logger.info("Fetching auction history for %s from API", item_id)
    try:
        raw = await stalcraft.get_item_price_history(
            item_id=item_id,
            region=region,
            limit=200,
            offset=0,
        )
    except Exception:
        logger.exception("Failed to fetch auction history for %s", item_id)
        # Возвращаем старый кэш если есть
        return await session.get(ItemPriceCache, (item_id, region))

    # Сохраняем сырые данные (INSERT OR IGNORE через on_conflict)
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    price_entries = raw.get("prices", [])
    if price_entries:
        for entry in price_entries:
            stmt = pg_insert(AuctionPriceHistory).values(
                item_id=item_id,
                region=region,
                amount=entry["amount"],
                price=entry["price"],
                sold_at=entry["time"],
                fetched_at=now,
            ).on_conflict_do_nothing(constraint="uq_auction_history")
            await session.execute(stmt)

    # Читаем накопленную историю из БД (последние 500 записей для расчёта)
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

    # Upsert кэша
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