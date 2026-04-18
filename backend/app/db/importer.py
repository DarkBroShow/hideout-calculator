import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Item, Perk, Recipe, RecipeIngredient

logger = logging.getLogger(__name__)

DB_PATH = Path("/game-data/stalcraft-database")


def _lines(obj: dict | None) -> dict:
    if not obj:
        return {}
    return obj.get("lines", {})


async def run_import(session: AsyncSession, region: str) -> None:
    region_path = DB_PATH / region
    if not region_path.exists():
        logger.warning("stalcraft-database region path not found: %s", region_path)
        return

    logger.info("Starting import for region: %s", region)

    await _truncate(session)
    await _import_items(session, region, region_path)
    await _import_recipes(session, region, region_path)
    await session.commit()

    logger.info("Import complete for region: %s", region)


async def _truncate(session: AsyncSession) -> None:
    logger.info("Truncating tables...")
    await session.execute(text("TRUNCATE recipe_ingredients, recipes, perks, items RESTART IDENTITY CASCADE"))


async def _import_items(session: AsyncSession, region: str, region_path: Path) -> None:
    listing_path = region_path / "listing.json"
    if not listing_path.exists():
        logger.warning("listing.json not found")
        return

    listing: list[dict] = json.loads(listing_path.read_text(encoding="utf-8"))
    logger.info("Importing %d items...", len(listing))

    for entry in listing:
        data_path_str: str = entry.get("data", "")
        parts = data_path_str.strip("/").split("/")
        if len(parts) < 3:
            continue

        item_id = parts[-1].removesuffix(".json")
        category = "/".join(parts[1:-1]) 

        item_file = region_path / Path(*parts)
        raw: dict = {}
        if item_file.exists():
            raw = json.loads(item_file.read_text(encoding="utf-8"))

        name_lines = _lines(entry.get("name"))

        session.add(Item(
            id=item_id,
            region=region,
            category=category,
            color=entry.get("color"),
            status_state=entry.get("status", {}).get("state"),
            icon_path=entry.get("icon"),
            name_ru=name_lines.get("ru"),
            name_en=name_lines.get("en"),
            name_es=name_lines.get("es"),
            name_fr=name_lines.get("fr"),
            name_ko=name_lines.get("ko"),
            raw=raw,
        ))

    await session.flush()


async def _import_recipes(session: AsyncSession, region: str, region_path: Path) -> None:
    recipes_path = region_path / "hideout_recipes.json"
    if not recipes_path.exists():
        logger.warning("hideout_recipes.json not found")
        return

    data: dict = json.loads(recipes_path.read_text(encoding="utf-8"))

    # Импортируем perks
    for perk in data.get("perks", []):
        name_lines = _lines(perk.get("name"))
        desc_lines = _lines(perk.get("desc"))
        session.add(Perk(
            id=perk["id"],
            region=region,
            name_ru=name_lines.get("ru"),
            name_en=name_lines.get("en"),
            desc_ru=desc_lines.get("ru"),
            desc_en=desc_lines.get("en"),
        ))

    await session.flush()

    # Импортируем рецепты
    recipes: list[dict] = data.get("recipes", [])
    logger.info("Importing %d recipes...", len(recipes))

    for recipe_data in recipes:
        results: list[dict] = recipe_data.get("result", [])
        if not results:
            continue

        result_item_id = results[0]["item"]
        result_amount = results[0].get("amount", 1)

        requirements: dict = recipe_data.get("requirements", {})
        perks_req: dict = requirements.get("perks", {})
        perk_id, perk_level = (None, None)
        if perks_req:
            perk_id, perk_level = next(iter(perks_req.items()))

        recipe = Recipe(
            region=region,
            bench=recipe_data.get("bench", "unknown"),
            result_item_id=result_item_id,
            result_amount=result_amount,
            energy=recipe_data.get("energy"),
            required_perk_id=perk_id,
            required_perk_level=perk_level,
            required_features=requirements.get("features", []),
            category_ru=_lines(recipe_data.get("category")).get("ru"),
            category_en=_lines(recipe_data.get("category")).get("en"),
            subcategory_ru=_lines(recipe_data.get("subcategory")).get("ru"),
            subcategory_en=_lines(recipe_data.get("subcategory")).get("en"),
        )
        session.add(recipe)
        await session.flush()

        for ing in recipe_data.get("ingredients", []):
            session.add(RecipeIngredient(
                recipe_id=recipe.id,
                item_id=ing["item"],
                amount=ing["amount"],
            ))