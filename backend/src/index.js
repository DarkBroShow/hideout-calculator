// ========================================
// 1. Импорты и инициализация
// ========================================
import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import pkg from "pg";

dotenv.config();

const { Pool } = pkg;

const app = express();
app.use(cors());
app.use(express.json());

const port = process.env.BACKEND_PORT || 4000;

// ========================================
// 2. Подключение к PostgreSQL
// ========================================
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

// небольшая проверка коннекта при старте
pool
  .query("SELECT NOW()")
  .then((r) => {
    console.log("DB connected, time:", r.rows[0].now);
  })
  .catch((e) => {
    console.error("DB connection error:", e);
  });

// ========================================
// 3. Функция — построение дерева рецепта
// ========================================
async function buildRecipeTree(
  itemId,
  depth = 0,
  maxDepth = 6,
  visited = new Set()
) {
  if (depth > maxDepth) {
    return { itemId, depth, truncated: true };
  }

  if (visited.has(itemId)) {
    return { itemId, cycle: true };
  }
  visited.add(itemId);

  // сам предмет
  const itemRes = await pool.query(
    "SELECT id, name_ru, category, rarity, icon_path FROM items WHERE id = $1",
    [itemId]
  );
  const item = itemRes.rows[0] || { id: itemId, name_ru: itemId };

  // рецепты, которые производят этот предмет
  const recRes = await pool.query(
    `
    SELECT id, result_item_id, result_amount, bench, energy, perk_id, perk_level
    FROM recipes
    WHERE result_item_id = $1
    ORDER BY id
    `,
    [itemId]
  );

  const recipes = [];

  for (const r of recRes.rows) {
    const ingRes = await pool.query(
      `
      SELECT ingredient_item_id, amount
      FROM recipe_ingredients
      WHERE recipe_id = $1
      ORDER BY id
      `,
      [r.id]
    );

    const ingredients = [];
    for (const ing of ingRes.rows) {
      const child = await buildRecipeTree(
        ing.ingredient_item_id,
        depth + 1,
        maxDepth,
        new Set(visited)
      );
      ingredients.push({
        itemId: ing.ingredient_item_id,
        amount: ing.amount,
        node: child,
      });
    }

    recipes.push({
      id: r.id,
      result_item_id: r.result_item_id,
      result_amount: r.result_amount,
      bench: r.bench,
      energy: r.energy,
      perk_id: r.perk_id,
      perk_level: r.perk_level,
      ingredients,
    });
  }

  return { item, recipes };
}

// ========================================
// 4. REST API: healthcheck и работа с БД
// ========================================

// healthcheck + проверка подключения к БД
app.get("/api/health", async (req, res) => {
  try {
    const result = await pool.query("SELECT NOW()");
    res.json({ status: "ok", time: result.rows[0].now });
  } catch (e) {
    console.error(e);
    res.status(500).json({ status: "error" });
  }
});

// поиск предметов по подстроке в локальной БД
app.get("/api/items/search", async (req, res) => {
  const q = (req.query.q || "").trim();
  if (!q) return res.json([]);

  try {
    const result = await pool.query(
      `
      SELECT id, name_ru, category, rarity, icon_path
      FROM items
      WHERE name_ru ILIKE $1
      ORDER BY name_ru
      LIMIT 50
      `,
      [`%${q}%`]
    );
    res.json(result.rows);
  } catch (e) {
    console.error("items search error:", e);
    res.status(500).json({ error: "db_error" });
  }
});

// получить дерево рецепта по itemId
app.get("/api/recipes/:itemId/tree", async (req, res) => {
  const itemId = req.params.itemId;
  try {
    const tree = await buildRecipeTree(itemId);
    res.json(tree);
  } catch (e) {
    console.error("recipe tree error:", e);
    res.status(500).json({ error: "failed_to_build_recipe_tree" });
  }
});

// ========================================
// 5. Старт сервера
// ========================================
app.listen(port, () => {
  console.log(`Backend listening on port ${port}`);
});