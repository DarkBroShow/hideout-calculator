import pkg from "pg";
import dotenv from "dotenv";

dotenv.config();

const { Pool } = pkg;
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function main() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS items (
      id        text PRIMARY KEY,
      name_ru   text NOT NULL,
      category  text,
      rarity    text,
      icon_path text,
      raw_json  jsonb
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS recipes (
      id             serial PRIMARY KEY,
      result_item_id text NOT NULL,
      result_amount  integer NOT NULL,
      bench          text,
      energy         numeric,
      perk_id        text,
      perk_level     integer,
      raw_json       jsonb NOT NULL
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS recipe_ingredients (
      id                 serial PRIMARY KEY,
      recipe_id          integer NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
      ingredient_item_id text NOT NULL,
      amount             integer NOT NULL
    );
  `);

  console.log("Schema ensured");
  await pool.end();
}

main().catch((e) => {
  console.error("Schema failed:", e);
  process.exit(1);
});