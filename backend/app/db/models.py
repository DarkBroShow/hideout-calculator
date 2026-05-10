from sqlalchemy import (
    BigInteger, Boolean, Float, ForeignKey,
    Integer, String, Text, DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

from datetime import datetime
from sqlalchemy import UniqueConstraint, BigInteger


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    region: Mapped[str] = mapped_column(String(8), nullable=False)
    category: Mapped[str] = mapped_column(String(128))
    color: Mapped[str | None] = mapped_column(String(32))
    status_state: Mapped[str | None] = mapped_column(String(32))
    icon_path: Mapped[str | None] = mapped_column(Text)

    name_ru: Mapped[str | None] = mapped_column(Text)
    name_en: Mapped[str | None] = mapped_column(Text)
    name_es: Mapped[str | None] = mapped_column(Text)
    name_fr: Mapped[str | None] = mapped_column(Text)
    name_ko: Mapped[str | None] = mapped_column(Text)

    raw: Mapped[dict] = mapped_column(JSONB, default={})

    recipes: Mapped[list["Recipe"]] = relationship(
        back_populates="result_item", foreign_keys="Recipe.result_item_id"
    )


class Perk(Base):
    __tablename__ = "perks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    region: Mapped[str] = mapped_column(String(8), primary_key=True)
    name_ru: Mapped[str | None] = mapped_column(Text)
    name_en: Mapped[str | None] = mapped_column(Text)
    desc_ru: Mapped[str | None] = mapped_column(Text)
    desc_en: Mapped[str | None] = mapped_column(Text)


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(String(8))
    bench: Mapped[str] = mapped_column(String(64))

    result_item_id: Mapped[str] = mapped_column(String(32), ForeignKey("items.id"), nullable=False)

    result_amount: Mapped[int] = mapped_column(Integer, default=1)
    energy: Mapped[float | None] = mapped_column(Float)

    required_perk_id: Mapped[str | None] = mapped_column(String(64))
    required_perk_level: Mapped[int | None] = mapped_column(Integer)
    required_features: Mapped[list] = mapped_column(JSONB, default=[])

    category_ru: Mapped[str | None] = mapped_column(Text)
    category_en: Mapped[str | None] = mapped_column(Text)
    subcategory_ru: Mapped[str | None] = mapped_column(Text)
    subcategory_en: Mapped[str | None] = mapped_column(Text)

    result_item: Mapped["Item"] = relationship(
        back_populates="recipes", foreign_keys=[result_item_id]
    )
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan"
    )


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(Integer, ForeignKey("recipes.id"))
    item_id: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column(Integer)

    recipe: Mapped["Recipe"] = relationship(back_populates="ingredients")


class AuctionPriceHistory(Base):
    """Сырые данные истории цен с аукциона."""
    __tablename__ = "auction_price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    region: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(BigInteger)
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("item_id", "region", "sold_at", name="uq_auction_history"),
    )


class ItemPriceCache(Base):
    """Агрегированная цена предмета (расчитывается коллектором из истории)."""
    __tablename__ = "item_price_cache"

    item_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    region: Mapped[str] = mapped_column(String(8), primary_key=True)

    buy_price: Mapped[int | None] = mapped_column(BigInteger)
    sell_price: Mapped[int | None] = mapped_column(BigInteger)
    fair_price: Mapped[int | None] = mapped_column(BigInteger)
    min_price: Mapped[int | None] = mapped_column(BigInteger)
    max_price: Mapped[int | None] = mapped_column(BigInteger)

    sales_per_day: Mapped[float | None] = mapped_column(Float)
    sample_size: Mapped[int | None] = mapped_column(Integer)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600)


class ItemRequestStats(Base):
    """Статистика запросов предметов пользователями.
    Используется коллектором для приоритизации сбора цен.
    """
    __tablename__ = "item_request_stats"

    item_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    region: Mapped[str] = mapped_column(String(8), primary_key=True)

    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CraftItem(Base):
    """Денормализованная таблица всех предметов, участвующих в рецептах убежища.
    Заполняется при старте из таблиц recipes и recipe_ingredients.
    Используется коллектором как base-set предметов, цены которых нужно отслеживать.
    """
    __tablename__ = "craft_items"

    item_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    region: Mapped[str] = mapped_column(String(8), primary_key=True)

    is_result: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # True = API вернул историю хотя бы раз. False = предмет не торгуется на аукционе
    # или ещё не был проверен. Коллектор обновляет это поле.
    auction_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Когда последний раз проверяли доступность (чтобы периодически перепроверять)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
