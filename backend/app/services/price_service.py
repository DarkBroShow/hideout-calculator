"""
price_service.py — ТОЛЬКО чтение из БД.

Все обращения к Stalcraft API перенесены в price_collector.py.
Этот модуль используется recipe_cost_service и роутерами.
"""
import logging
import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.game_config import AUCTION_COMMISSION, TTL_TIERS
from app.db.models import AuctionPriceHistory, ItemPriceCache
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Вспомогательные функции (также используются коллектором)
# ---------------------------------------------------------------------------

def calc_ttl(sales_per_day: float) -> int:
    """Адаптивный TTL в секундах — пороги берутся из game_config.TTL_TIERS."""
    for min_sales, ttl in TTL_TIERS:
        if sales_per_day >= min_sales:
            return ttl
    return TTL_TIERS[-1][1]


def calc_percentile(prices: list[int], p: float) -> int:
    """p от 0.0 до 1.0"""
    if not prices:
        return 0
    sorted_p = sorted(prices)
    idx = int(len(sorted_p) * p)
    return sorted_p[min(idx, len(sorted_p) - 1)]


def fair_price_from_history(rows: list[AuctionPriceHistory]) -> dict:
    """Агрегирует историю продаж в метрики цен.
    Возвращает пустой словарь если данных нет.
    """
    if not rows:
        return {}

    single_sales = [r for r in rows if r.amount == 1]
    all_prices = sorted(r.price for r in rows)

    sell_source = single_sales if len(single_sales) >= 10 else rows
    sell_prices = sorted(r.price for r in sell_source)

    # p60 одиночных продаж — реалистичная цена продажи до комиссии
    sell_idx = int(len(sell_prices) * 0.60)
    sell_price_before_tax = sell_prices[min(sell_idx, len(sell_prices) - 1)]
    sell_price = int(sell_price_before_tax * (1 - AUCTION_COMMISSION))

    # p25 всех цен — временная цена закупки (перезапишется из лотов)
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
        "ttl_seconds": calc_ttl(sales_per_day),
    }


# ---------------------------------------------------------------------------
# Публичный API — только БД
# ---------------------------------------------------------------------------

async def get_fair_price(
    item_id: str,
    session: AsyncSession,
    region: str | None = None,
) -> ItemPriceCache | None:
    """Возвращает кэшированную цену из БД.
    Никаких обращений к Stalcraft API — данные обновляются коллектором.
    Если данных нет или кэш устарел — возвращает то что есть (или None).
    """
    region = region or settings.stalcraft_region
    cache_row = await session.get(ItemPriceCache, (item_id, region))

    if cache_row is None:
        logger.debug("price cache miss: %s [%s]", item_id, region)
        return None

    now = datetime.now(timezone.utc)
    expires_at = cache_row.updated_at + timedelta(seconds=cache_row.ttl_seconds)
    if now > expires_at:
        logger.debug(
            "price cache stale: %s [%s] (expired %s ago)",
            item_id, region,
            str(now - expires_at).split(".")[0],
        )

    return cache_row
