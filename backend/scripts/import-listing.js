import fs from "fs";
import path from "path";
import url from "url";
import pkg from "pg";
import dotenv from "dotenv";

dotenv.config();

const { Pool } = pkg;

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));
const listingPath = path.join(
  __dirname,
  "..",
  "stalcraft-database",
  "ru",
  "listing.json"
);

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function main() {
  const raw = await fs.promises.readFile(listingPath, "utf-8");
  const listing = JSON.parse(raw);

  console.log("Total listing entries:", listing.length);

  for (const entry of listing) {
    const dataPath = entry.data; // "/items/medicine/9mmq.json"
    const iconPath = entry.icon; // "/icons/medicine/9mmq.png"
    const nameRu = entry.name?.lines?.ru || "";
    const rarity = entry.color || null;

    // id = последний сегмент data без .json
    const id = dataPath.split("/").pop().replace(".json", "");
    const category = dataPath.split("/")[2] || null; // "medicine" в примере

    await pool.query(
      `
      INSERT INTO items (id, name_ru, category, rarity, icon_path)
      VALUES ($1, $2, $3, $4, $5)
      ON CONFLICT (id) DO UPDATE
        SET name_ru   = EXCLUDED.name_ru,
            category  = EXCLUDED.category,
            rarity    = EXCLUDED.rarity,
            icon_path = EXCLUDED.icon_path
      `,
      [id, nameRu, category, rarity, iconPath]
    );
  }

  console.log("Listing import finished");
  await pool.end();
}

main().catch((e) => {
  console.error("Listing import failed:", e);
  process.exit(1);
});