import fs from "fs";
import path from "path";
import url from "url";
import pkg from "pg";
import dotenv from "dotenv";

dotenv.config();

const { Pool } = pkg;

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const dbRoot = path.join(__dirname, "..", "stalcraft-database", "ru", "items");

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function importItemFile(filePath) {
  const raw = await fs.promises.readFile(filePath, "utf-8");
  const json = JSON.parse(raw);

  const id = json.id;
  const category = json.category || null;
  const nameRu = json.name?.lines?.ru || json.name?.text || id;
  const rarity = json.color || null;

  await pool.query(
    `
    INSERT INTO items (id, name_ru, category, rarity, raw_json)
    VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT (id) DO UPDATE
      SET raw_json = EXCLUDED.raw_json
    `,
    [id, nameRu, category, rarity, json]
  );
}

async function walkDir(dir) {
  const entries = await fs.promises.readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      await walkDir(fullPath);
    } else if (entry.isFile() && entry.name.endsWith(".json")) {
      await importItemFile(fullPath);
    }
  }
}

async function main() {
  console.log("Importing items raw_json from", dbRoot);
  try {
    await walkDir(dbRoot);
    console.log("Items import finished");
  } catch (e) {
    console.error("Items import failed:", e);
  } finally {
    await pool.end();
  }
}

main();