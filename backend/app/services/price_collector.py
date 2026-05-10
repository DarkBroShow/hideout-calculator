"""
price_collector.py — Фоновая служба сбора цен с аукциона Stalcraft.

Архитектура:
  • Единственный компонент, который обращается к Stalcraft API.
  • Строит приоритетную очередь: горячие предметы (по запросам пользователей) →
    предметы с истёкшим TTL → все craft-предметы по давности обновления.
  • Умная стратегия fetch: холодный (limit=190) при отсутствии данных,
    инкрементальный (limit=20, offset++) пока не покроем окно 48 ч.
  • Пересчитывает item_price_cache после каждого обновления.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func, text, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.game_config import (
    COLLECTOR_BATCH_SIZE,
    COLLECTOR_CYCLE_INTERVAL_SECONDS,
    COLLECTOR_DELAY_BETWEEN_REQUESTS,
    COLLECTOR_HISTORY_LIMIT_COLD,
    COLLECTOR_HISTORY_LIMIT_INCREMENTAL,
    COLLECTOR_HISTORY_MAX_OFFSET,
    COLLECTOR_HISTORY_WINDOW_DAYS,
    COLLECTOR_LOTS_LIMIT,
    COLLECTOR_REQUEST_BOOST_WEIGHT,
    COLLECTOR_REQUEST_RECENCY_WINDOW,
)
from app.db.base import async_session_factory
from app.db.models import (
    AuctionPriceHistory,
    CraftItem,
    ItemPriceCache,
    ItemRequestStats,
    Recipe,
    RecipeIngredient,
)
from app.services.price_service import fair_price_from_history, calc_ttl
from app.services.stalcraft_client import StalcraftClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Заполнение таблицы craft_items
# ---------------------------------------------------------------------------

async def populate_craft_items(session: AsyncSession, region: str) -> None:
    """Заполняет/обновляет таблицу CraftItem из рецептов убежища.
    Включает: ингредиенты (is_result=False) + результаты крафта (is_result=True).
    Не включает бартерные предметы прокачки (они не в recipe_ingredients).
    """
    logger.info("Populating craft_items for region=%s ...", region)

    # Все ингредиенты
    ingredient_ids: set[str] = set(
        (await session.execute(
            select(RecipeIngredient.item_id)
            .join(Recipe, Recipe.id == RecipeIngredient.recipe_id)
            .where(Recipe.region == region)
            .distinct()
        )).scalars().all()
    )

    # Все результаты крафта
    result_ids: set[str] = set(
        (await session.execute(
            select(Recipe.result_item_id)
            .where(Recipe.region == region)
            .distinct()
        )).scalars().all()
    )

    all_ids = ingredient_ids | result_ids

    if not all_ids:
        logger.warning("No craft items found for region=%s — recipes table empty?", region)
        return

    rows = []
    for item_id in all_ids:
        rows.append({
            "item_id": item_id,
            "region": region,
            "is_result": item_id in result_ids,
        })

    stmt = pg_insert(CraftItem).values(rows).on_conflict_do_update(
        index_elements=["item_id", "region"],
        set_={"is_result": pg_insert(CraftItem).excluded.is_result},
    )
    await session.execute(stmt)
    await session.commit()

    logger.info(
        "craft_items populated: %d items (%d ingredients, %d results) for region=%s",
        len(all_ids), len(ingredient_ids), len(result_ids), region,
    )


# ---------------------------------------------------------------------------
# Основной коллектор
# ---------------------------------------------------------------------------

class PriceCollector:
    """Фоновая служба непрерывного сбора цен."""

    def __init__(self, region: str | None = None):
        self.region = region or settings.stalcraft_region
        self._stalcraft = StalcraftClient()
        self._running = False
        self._cycle_count = 0

    async def start(self) -> None:
        """Запустить коллектор (блокирует до остановки)."""
        self._running = True
        logger.info(
            "PriceCollector started [region=%s, batch=%d, interval=%ds]",
            self.region, COLLECTOR_BATCH_SIZE, COLLECTOR_CYCLE_INTERVAL_SECONDS,
        )
        await self._run_loop()

    async def stop(self) -> None:
        """Остановить коллектор и закрыть HTTP-клиент."""
        logger.info("PriceCollector stopping...")
        self._running = False
        await self._stalcraft.aclose()

    # ------------------------------------------------------------------
    # Основной цикл
    # ------------------------------------------------------------------

    async def _run_loop(self) -> None:
        while self._running:
            self._cycle_count += 1
            logger.info("PriceCollector cycle #%d started", self._cycle_count)
            try:
                await self._process_batch()
            except Exception:
                logger.exception("PriceCollector cycle #%d failed", self._cycle_count)

            logger.info(
                "PriceCollector cycle #%d done, sleeping %ds",
                self._cycle_count, COLLECTOR_CYCLE_INTERVAL_SECONDS,
            )
            await asyncio.sleep(COLLECTOR_CYCLE_INTERVAL_SECONDS)

    async def _process_batch(self) -> None:
        async with async_session_factory() as session:
            priority_items = await self._get_priority_items(session)

        if not priority_items:
            logger.info("PriceCollector: priority queue empty, nothing to do")
            return

        batch = priority_items[:COLLECTOR_BATCH_SIZE]
        logger.info(
            "PriceCollector: processing %d/%d items this cycle",
            len(batch), len(priority_items),
        )

        for idx, item_id in enumerate(batch, 1):
            if not self._running:
                break
            try:
                async with async_session_factory() as session:
                    await self._refresh_item(item_id, session)
                logger.debug(
                    "PriceCollector [%d/%d] refreshed %s",
                    idx, len(batch), item_id,
                )
            except Exception:
                logger.exception("PriceCollector: failed to refresh %s", item_id)

            await asyncio.sleep(COLLECTOR_DELAY_BETWEEN_REQUESTS)

    # ------------------------------------------------------------------
    # Приоритизация
    # ------------------------------------------------------------------

    async def _get_priority_items(self, session: AsyncSession) -> list[str]:
        """Строит отсортированный по приоритету список item_id для обновления.

        Алгоритм:
          score = request_boost + staleness_score
          request_boost = request_count * WEIGHT  (только «свежие» запросы)
          staleness_score = max(0, (now - updated_at) / ttl_seconds)
                             999 если запись в кэше отсутствует
        """
        now = datetime.now(timezone.utc)
        recency_cutoff = now - timedelta(seconds=COLLECTOR_REQUEST_RECENCY_WINDOW)

        # 1. Все craft-предметы региона
        craft_ids_result = await session.execute(
            select(CraftItem.item_id).where(CraftItem.region == self.region)
        )
        craft_ids: list[str] = list(craft_ids_result.scalars().all())

        if not craft_ids:
            logger.warning(
                "PriceCollector: craft_items empty for region=%s, "
                "run populate_craft_items() first",
                self.region,
            )
            return []

        # 2. Кэш цен (обновлённость)
        cache_map: dict[str, ItemPriceCache] = {}
        cache_rows = (await session.execute(
            select(ItemPriceCache).where(
                ItemPriceCache.item_id.in_(craft_ids),
                ItemPriceCache.region == self.region,
            )
        )).scalars().all()
        for row in cache_rows:
            cache_map[row.item_id] = row

        # 3. Статистика запросов (только свежие)
        request_map: dict[str, int] = {}
        request_rows = (await session.execute(
            select(ItemRequestStats).where(
                ItemRequestStats.item_id.in_(craft_ids),
                ItemRequestStats.region == self.region,
                ItemRequestStats.last_requested_at >= recency_cutoff,
            )
        )).scalars().all()
        for row in request_rows:
            request_map[row.item_id] = row.request_count

        # 4. Вычисляем score для каждого предмета
        scored: list[tuple[float, str]] = []
        for item_id in craft_ids:
            cache = cache_map.get(item_id)
            req_count = request_map.get(item_id, 0)

            request_boost = req_count * COLLECTOR_REQUEST_BOOST_WEIGHT

            if cache is None:
                staleness = 999.0  # Никогда не собирали
            else:
                elapsed = (now - cache.updated_at).total_seconds()
                staleness = elapsed / max(cache.ttl_seconds, 1)

            score = request_boost + staleness
            scored.append((score, item_id))

        # Сортируем по убыванию score (самые приоритетные — первые)
        scored.sort(key=lambda x: x[0], reverse=True)

        logger.debug(
            "PriceCollector priority queue: %d items, top5=%s",
            len(scored),
            [(iid, round(sc, 1)) for sc, iid in scored[:5]],
        )
        return [item_id for _, item_id in scored]

    # ------------------------------------------------------------------
    # Сбор данных по одному предмету
    # ------------------------------------------------------------------

    async def _refresh_item(self, item_id: str, session: AsyncSession) -> None:
        """Обновляет историю и кэш цен для одного предмета."""
        logger.debug("PriceCollector: refreshing %s [%s]", item_id, self.region)

        history_new = await self._fetch_history_smart(item_id, session)
        buy_price = await self._fetch_buy_price(item_id)
        await self._recompute_cache(item_id, session, buy_price=buy_price)

        logger.info(
            "PriceCollector: %s — +%d history records, buy_price=%s",
            item_id, history_new, buy_price,
        )

    async def _fetch_history_smart(
        self,
        item_id: str,
        session: AsyncSession,
    ) -> int:
        """Умный инкрементальный сбор истории.

        Если данных нет или они устарели — холодный fetch (limit=190).
        Иначе — инкрементальный с offset пока не покроем окно WINDOW_DAYS.
        Возвращает количество новых записей добавленных в БД.
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=COLLECTOR_HISTORY_WINDOW_DAYS)

        # Проверяем наличие свежих данных
        latest_sold_result = await session.execute(
            select(func.max(AuctionPriceHistory.sold_at)).where(
                AuctionPriceHistory.item_id == item_id,
                AuctionPriceHistory.region == self.region,
            )
        )
        latest_sold_at: datetime | None = latest_sold_result.scalar()

        has_recent = latest_sold_at is not None and latest_sold_at > window_start

        if not has_recent:
            logger.info(
                "PriceCollector: cold fetch for %s (latest=%s)",
                item_id, latest_sold_at,
            )
            new_count, _ = await self._fetch_history_page(
                item_id, session,
                limit=COLLECTOR_HISTORY_LIMIT_COLD,
                offset=0,
            )
            return new_count

        # Инкрементальный режим: paginate пока не покроем окно
        logger.debug("PriceCollector: incremental fetch for %s", item_id)
        total_new = 0
        offset = 0

        while offset <= COLLECTOR_HISTORY_MAX_OFFSET:
            new_count, oldest_in_batch = await self._fetch_history_page(
                item_id, session,
                limit=COLLECTOR_HISTORY_LIMIT_INCREMENTAL,
                offset=offset,
            )
            total_new += new_count

            if new_count == 0:
                # Все записи уже в БД — актуальны
                logger.debug(
                    "PriceCollector: %s incremental — all known at offset=%d",
                    item_id, offset,
                )
                break

            if oldest_in_batch is None or oldest_in_batch < window_start:
                # Вышли за пределы окна — покрыли всё нужное
                logger.debug(
                    "PriceCollector: %s incremental — window covered at offset=%d",
                    item_id, offset,
                )
                break

            offset += COLLECTOR_HISTORY_LIMIT_INCREMENTAL
            await asyncio.sleep(COLLECTOR_DELAY_BETWEEN_REQUESTS)

        return total_new

    async def _fetch_history_page(
        self,
        item_id: str,
        session: AsyncSession,
        limit: int,
        offset: int,
    ) -> tuple[int, datetime | None]:
        """Загружает одну страницу истории продаж.

        Возвращает (количество_новых_записей, дата_самой_старой_записи_в_батче).
        """
        try:
            raw = await self._stalcraft.get_item_price_history(
                item_id=item_id,
                region=self.region,
                limit=limit,
                offset=offset,
            )
        except Exception:
            logger.exception(
                "PriceCollector: history API error for %s (limit=%d, offset=%d)",
                item_id, limit, offset,
            )
            return 0, None

        price_entries = raw.get("prices", [])
        if not price_entries:
            return 0, None

        now = datetime.now(timezone.utc)
        new_count = 0
        oldest: datetime | None = None

        for entry in price_entries:
            amount = entry.get("amount", 1)
            raw_price = entry.get("price", 0)
            price_per_unit = raw_price // amount if amount > 0 else raw_price
            sold_at = datetime.fromisoformat(
                entry["time"].replace("Z", "+00:00")
            )

            if oldest is None or sold_at < oldest:
                oldest = sold_at

            stmt = pg_insert(AuctionPriceHistory).values(
                item_id=item_id,
                region=self.region,
                amount=amount,
                price=price_per_unit,
                sold_at=sold_at,
                fetched_at=now,
            ).on_conflict_do_nothing(constraint="uq_auction_history")

            result = await session.execute(stmt)
            if result.rowcount and result.rowcount > 0:
                new_count += 1

        await session.commit()
        return new_count, oldest

    async def _fetch_buy_price(self, item_id: str) -> int | None:
        """Получает текущую цену закупки из активных лотов."""
        try:
            raw = await self._stalcraft.get_item_lots(
                item_id=item_id,
                region=self.region,
                limit=COLLECTOR_LOTS_LIMIT,
                offset=0,
                sort="current_price",
                order="asc",
            )
        except Exception:
            logger.exception("PriceCollector: lots API error for %s", item_id)
            return None

        lots = raw.get("lots", [])
        if not lots:
            return None

        def price_per_unit(lot: dict) -> int:
            buyout = lot.get("buyoutPrice") or lot.get("currentPrice") or 0
            amount = lot.get("amount", 1)
            return buyout // amount if amount > 0 else buyout

        single_lots = [l for l in lots if l.get("amount", 1) == 1]
        bulk_lots = [l for l in lots if l.get("amount", 1) > 1]

        if single_lots:
            prices = sorted(price_per_unit(l) for l in single_lots)
            idx = max(0, int(len(prices) * 0.25))
            return prices[idx]

        if bulk_lots:
            prices = sorted(price_per_unit(l) for l in bulk_lots)
            return prices[0]

        return None

    async def _recompute_cache(
        self,
        item_id: str,
        session: AsyncSession,
        buy_price: int | None = None,
    ) -> None:
        """Пересчитывает item_price_cache из auction_price_history."""
        history_rows = (
            await session.execute(
                select(AuctionPriceHistory)
                .where(
                    AuctionPriceHistory.item_id == item_id,
                    AuctionPriceHistory.region == self.region,
                )
                .order_by(AuctionPriceHistory.sold_at.desc())
                .limit(500)
            )
        ).scalars().all()

        agg = fair_price_from_history(list(history_rows))
        if not agg:
            logger.warning(
                "PriceCollector: no history to aggregate for %s", item_id
            )
            return

        if buy_price is not None:
            agg["buy_price"] = buy_price
            agg["fair_price"] = buy_price

        now = datetime.now(timezone.utc)
        stmt = pg_insert(ItemPriceCache).values(
            item_id=item_id,
            region=self.region,
            updated_at=now,
            **agg,
        ).on_conflict_do_update(
            index_elements=["item_id", "region"],
            set_={**agg, "updated_at": now},
        )
        await session.execute(stmt)
        await session.commit()

        logger.debug(
            "PriceCollector: cache updated %s — buy=%s sell=%s ttl=%ds",
            item_id, agg.get("buy_price"), agg.get("sell_price"), agg.get("ttl_seconds", 0),
        )
