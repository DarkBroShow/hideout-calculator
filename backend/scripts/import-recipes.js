import fs from "fs";
import path from "path";
import url from "url";
import pkg from "pg";
import dotenv from "dotenv";

dotenv.config();

const { Pool } = pkg;

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const recipesPath = path.join(
  __dirname,
  "..",
  "stalcraft-database",
  "ru",
  "hideout_recipes.json"
);

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function main() {
  const raw = await fs.promises.readFile(recipesPath, "utf-8");
  const json = JSON.parse(raw);

  const recipes = json.recipes || [];
  console.log("Total recipes:", recipes.length);

  // очищаем таблицы перед импортом
  await pool.query("TRUNCATE TABLE recipe_ingredients RESTART IDENTITY CASCADE");
  await pool.query("TRUNCATE TABLE recipes RESTART IDENTITY CASCADE");

  for (const r of recipes) {
    const bench = r.bench || null;
    const energy = r.energy ?? null;

    const result0 = (r.result && r.result[0]) || null;
    if (!result0) continue;

    const resultItemId = result0.item;
    const resultAmount = result0.amount ?? 1;

    let perkId = null;
    let perkLevel = null;
    if (r.requirements && r.requirements.perks) {
      const entries = Object.entries(r.requirements.perks);
      if (entries.length > 0) {
        [perkId, perkLevel] = entries[0];
      }
    }

    const res = await pool.query(
      `
      INSERT INTO recipes
        (result_item_id, result_amount, bench, energy, perk_id, perk_level, raw_json)
      VALUES ($1, $2, $3, $4, $5, $6, $7)
      RETURNING id
      `,
      [resultItemId, resultAmount, bench, energy, perkId, perkLevel, r]
    );

    const recipeId = res.rows[0].id;

    for (const ing of r.ingredients || []) {
      const ingredientId = ing.item;
      const amount = ing.amount ?? 1;

      await pool.query(
        `
        INSERT INTO recipe_ingredients (recipe_id, ingredient_item_id, amount)
        VALUES ($1, $2, $3)
        `,
        [recipeId, ingredientId, amount]
      );
    }
  }

  await pool.end();
  console.log("Recipes import finished");
}

main().catch((e) => {
  console.error("Import failed:", e);
  process.exit(1);
});