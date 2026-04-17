from sqlalchemy import (
    BigInteger, Boolean, Float, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    region: Mapped[str] = mapped_column(String(8), nullable=False)
    category: Mapped[str] = mapped_column(String(128))
    color: Mapped[str | None] = mapped_column(String(32))
    status_state: Mapped[str | None] = mapped_column(String(32))
    icon_path: Mapped[str | None] = mapped_column(Text)

    # Имена на всех языках
    name_ru: Mapped[str | None] = mapped_column(Text)
    name_en: Mapped[str | None] = mapped_column(Text)
    name_es: Mapped[str | None] = mapped_column(Text)
    name_fr: Mapped[str | None] = mapped_column(Text)
    name_ko: Mapped[str | None] = mapped_column(Text)

    # Полный JSON item-файла для будущих нужд
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

    # Требования
    required_perk_id: Mapped[str | None] = mapped_column(String(64))
    required_perk_level: Mapped[int | None] = mapped_column(Integer)
    required_features: Mapped[list] = mapped_column(JSONB, default=[])

    # Переводы категории/подкатегории
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